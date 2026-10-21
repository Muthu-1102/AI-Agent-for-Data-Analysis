import io
import os
import sys
import uuid
import base64
import contextlib
import subprocess
import asyncio
from typing import Dict, Any

from config import settings
from core.pipeline import PipelineStep, step_logging_wrapper
from utils.sandbox import Sandbox
from utils.helpers import resolve_dataset_path

# Isolated script template executed in child process
CHILD_RUNNER_TEMPLATE = """
import sys
import os
import contextlib
import io
import pandas as pd

# Headless matplotlib configuration
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.show = lambda *args, **kwargs: None

from utils.sandbox import Sandbox
from utils.helpers import load_and_clean_dataset

file_id = sys.argv[1]
plot_path = sys.argv[2]
code = sys.stdin.read()

# Normalize plot save paths in generated code to unique per-request plot_path
if "output_plot.png" in code:
    code = code.replace("output_plot.png", plot_path)

df = load_and_clean_dataset(file_id)

safe_globals = {
    "__builtins__": Sandbox.get_safe_builtins(),
    "pd": pd,
    "df": df,
    "plt": plt
}

try:
    import numpy as np
    safe_globals["np"] = np
except ImportError:
    pass

try:
    import seaborn as sns
    safe_globals["sns"] = sns
except ImportError:
    pass

safe_locals = {}

try:
    exec(code, safe_globals, safe_locals)
except Exception as e:
    import traceback
    sys.stderr.write(traceback.format_exc())
    sys.exit(1)
"""

class ExecutionAgent(PipelineStep):
    """
    Python Runtime Engineer Agent responsible for safely executing the validated Python code.
    Executes code in an isolated subprocess with a strict wall-clock timeout
    (enforcing SANDBOX_TIMEOUT_SECONDS) and per-request unique plot filenames.
    """
    
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        generated_code = state.get("generated_code")
        file_id = state.get("file_id")
        
        if not generated_code:
            raise ValueError("ExecutionAgent requires 'generated_code' in the state context.")
        if not file_id:
            raise ValueError("ExecutionAgent requires a valid 'file_id' to load the dataset.")
            
        # 1. Validate dataset existence
        try:
            resolve_dataset_path(file_id)
        except Exception as e:
            raise RuntimeError(f"Execution failed: Unable to locate dataset '{file_id}'. {str(e)}")

        # 2. Validate AST security constraints
        if not Sandbox.is_safe_code(generated_code):
            raise PermissionError("Execution blocked: Generated AI code contained forbidden or unsafe modules.")

        # 3. Provision unique per-request plot path
        plot_filename = f"plot_{uuid.uuid4().hex[:8]}.png"
        timeout_seconds = getattr(settings, "SANDBOX_TIMEOUT_SECONDS", 30)

        # 4. Execute in an isolated subprocess with hard wall-clock timeout
        def _run_subprocess():
            # Determine correct working directory (ensure backend modules resolve)
            backend_dir = os.path.abspath("backend")
            cwd = backend_dir if os.path.exists(backend_dir) else os.path.abspath(".")
            
            proc = subprocess.run(
                [sys.executable, "-c", CHILD_RUNNER_TEMPLATE, file_id, plot_filename],
                input=generated_code,
                text=True,
                capture_output=True,
                cwd=cwd,
                timeout=timeout_seconds
            )
            return proc

        execution_success = False
        error_trace = None
        captured_output = ""
        
        try:
            proc_result = await asyncio.to_thread(_run_subprocess)
            if proc_result.returncode == 0:
                execution_success = True
                captured_output = proc_result.stdout.strip()
            else:
                execution_success = False
                error_trace = proc_result.stderr.strip() or "Process exited with non-zero status"
        except subprocess.TimeoutExpired:
            execution_success = False
            error_trace = f"Execution timed out after {timeout_seconds} seconds (SANDBOX_TIMEOUT_SECONDS enforced)."
        except Exception as e:
            execution_success = False
            error_trace = f"Execution runtime error: {str(e)}"

        # 5. Extract plot if generated
        chart_image_base64 = None
        full_plot_path = os.path.join(os.path.abspath("backend"), plot_filename)
        if not os.path.exists(full_plot_path):
            full_plot_path = os.path.abspath(plot_filename)
            
        if os.path.exists(full_plot_path):
            try:
                with open(full_plot_path, "rb") as plot_file:
                    chart_image_base64 = base64.b64encode(plot_file.read()).decode("utf-8")
            except Exception:
                chart_image_base64 = None
            finally:
                try:
                    os.remove(full_plot_path)
                except Exception:
                    pass

        return {
            "execution_success": execution_success,
            "captured_output": captured_output,
            "error_trace": error_trace,
            "chart_image_base64": chart_image_base64
        }
