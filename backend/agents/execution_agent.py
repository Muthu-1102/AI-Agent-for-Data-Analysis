import io
import os
import base64
import contextlib
import traceback
from typing import Dict, Any
import pandas as pd

from core.pipeline import PipelineStep, step_logging_wrapper
from utils.sandbox import Sandbox
from utils.helpers import load_and_clean_dataset, resolve_dataset_path

class ExecutionAgent(PipelineStep):
    """
    Python Runtime Engineer Agent responsible for safely executing the validated Python code.
    It provisions a restricted global execution environment, pre-loads the user's DataFrame,
    executes the code, and securely captures all terminal outputs (stdout) and errors.
    """
    
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        generated_code = state.get("generated_code")
        file_id = state.get("file_id")
        
        if not generated_code:
            raise ValueError("ExecutionAgent requires 'generated_code' in the state context.")
        if not file_id:
            raise ValueError("ExecutionAgent requires a valid 'file_id' to load the dataset.")
            
        # 1. Load the actual dataset into memory as 'df'
        try:
            df = load_and_clean_dataset(file_id)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Execution failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Execution failed: Unable to load dataset. {str(e)}")

        # Validate AST constraints before even trying
        if not Sandbox.is_safe_code(generated_code):
            raise RuntimeError("Execution blocked: Generated AI code contained forbidden or unsafe modules.")

        # 2. Setup the restricted execution environment (globals)
        safe_globals = {
            "__builtins__": Sandbox.get_safe_builtins(),
            "pd": pd,
            "df": df
        }
        
        # Inject optional safe modules if they were requested / permitted
        try:
            import numpy as np
            safe_globals["np"] = np
        except ImportError:
            pass
            
        try:
            import matplotlib.pyplot as plt
            safe_globals["plt"] = plt
        except ImportError:
            pass
            
        try:
            import seaborn as sns
            safe_globals["sns"] = sns
        except ImportError:
            pass

        # 3. Execution Phase - Capture Outputs
        output_buffer = io.StringIO()
        execution_success = False
        error_trace = None
        
        # We use empty locals dict to avoid polluting globals with script variables
        safe_locals = {}

        try:
            # Redirect stdout to catch print() statements from the script
            with contextlib.redirect_stdout(output_buffer):
                # Execute the dynamically generated code securely
                exec(generated_code, safe_globals, safe_locals)
            execution_success = True
            
        except Exception as e:
            execution_success = False
            error_trace = traceback.format_exc()
            
        # 4. Gather Results
        captured_output = output_buffer.getvalue().strip()
        chart_image_base64 = None

        # If the executed code saved a plot to disk, include it in the pipeline state.
        plot_path = "output_plot.png"
        if os.path.exists(plot_path):
            try:
                with open(plot_path, "rb") as plot_file:
                    chart_image_base64 = base64.b64encode(plot_file.read()).decode("utf-8")
            except Exception:
                chart_image_base64 = None
            finally:
                try:
                    os.remove(plot_path)
                except Exception:
                    pass

        # Return complete execution metrics
        return {
            "execution_success": execution_success,
            "captured_output": captured_output,
            "error_trace": error_trace,
            "chart_image_base64": chart_image_base64
        }
