import logging
from typing import Dict, Any

from config import settings
from agents.schema_agent import SchemaAgent
from agents.prompt_agent import PromptAgent
from agents.code_agent import CodeAgent
from agents.validation_agent import ValidationAgent
from agents.execution_agent import ExecutionAgent
from agents.report_agent import ReportAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    The main Multi-Agent orchestrator that acts as the pipeline controller.
    It governs the lifecycle of a query by executing specialized agents sequentially,
    managing state transitions, and handling failure recoveries dynamically.
    """
    
    def __init__(self):
        self.schema_agent = SchemaAgent()
        self.prompt_agent = PromptAgent()
        self.code_agent = CodeAgent()
        self.validation_agent = ValidationAgent()
        self.execution_agent = ExecutionAgent()
        self.report_agent = ReportAgent()
        
    async def execute_pipeline(self, query: str, file_id: str) -> Dict[str, Any]:
        """
        Executes the full AI analysis pipeline for the requested query and dataset.
        """
        logger.info(f"Starting Multi-Agent Pipeline for file {file_id}. Task: '{query}'")
        
        # State Dictionary used as a shared memory bus between agents.
        # Keys here are read directly by downstream agents.
        state: Dict[str, Any] = {
            "query": query,
            "user_query": query,   # Alias used by PromptAgent / ReportAgent
            "file_id": file_id,
            "errors": [],
            "execution_success": False
        }
        
        try:
            # Step 1: SchemaAgent → extracts columns, dtypes, sample_rows
            state = await self._run_agent(self.schema_agent, state)
            
            # Step 2: PromptAgent → builds structured_prompt
            state = await self._run_agent(self.prompt_agent, state)
            
            # Feedback-driven Self-Repair Loop: CodeAgent -> ValidationAgent -> ExecutionAgent
            max_repair_attempts = settings.MAX_RETRIES
            repair_attempt = 0
            code_exec_ok = False
            last_repair_error = None
            
            while repair_attempt < max_repair_attempts:
                repair_attempt += 1
                state["repair_attempt"] = repair_attempt
                logger.info(f"Self-repair execution cycle ({repair_attempt}/{max_repair_attempts})")
                
                # Step 3: CodeAgent (incorporates state['repair_feedback'] if present)
                state = await self._run_agent(self.code_agent, state)
                
                # Step 4: ValidationAgent
                try:
                    val_res = await self.validation_agent.process(state)
                    state.update(val_res)
                except Exception as val_err:
                    last_repair_error = f"Code Validation Error: {str(val_err)}"
                    state["repair_feedback"] = last_repair_error
                    logger.warning(f"Validation rejected code on cycle {repair_attempt}/{max_repair_attempts}: {str(val_err)}. Feeding error to CodeAgent...")
                    continue
                    
                # Step 5: ExecutionAgent
                try:
                    exec_res = await self.execution_agent.process(state)
                    state.update(exec_res)
                    if state.get("execution_success"):
                        code_exec_ok = True
                        break
                    else:
                        last_repair_error = f"Runtime Execution Exception:\n{state.get('error_trace', 'Non-zero returncode')}"
                        state["repair_feedback"] = last_repair_error
                        logger.warning(f"Execution failed on cycle {repair_attempt}/{max_repair_attempts}. Feeding traceback to CodeAgent...")
                        continue
                except Exception as exec_err:
                    last_repair_error = f"Execution Exception: {str(exec_err)}"
                    state["repair_feedback"] = last_repair_error
                    logger.warning(f"Execution crashed on cycle {repair_attempt}/{max_repair_attempts}: {str(exec_err)}. Feeding traceback to CodeAgent...")
                    continue
                    
            if not code_exec_ok:
                logger.warning(f"Self-repair loop exhausted after {max_repair_attempts} attempts. Last failure: {last_repair_error}")
            
            # Step 6: ReportAgent → insights_summary, report_generated
            state = await self._run_agent(self.report_agent, state)
            
            is_success = bool(state.get("execution_success", False))
            status_str = "completed" if is_success else "failed"
            
            logger.info(f"Pipeline finished for query: '{query}' with status: {status_str}")
            return {
                "status": status_str,
                "execution_success": is_success,
                "insights_summary": state.get("insights_summary", ""),
                "generated_code": state.get("generated_code", ""),
                "captured_output": state.get("captured_output", ""),
                "chart_image_base64": state.get("chart_image_base64"),
                "error": None if is_success else (state.get("error_trace") or last_repair_error)
            }
            
        except RuntimeError as crit_err:
            logger.error(f"Pipeline failed at agent level: {str(crit_err)}")
            return {
                "status": "error",
                "insights_summary": None,
                "generated_code": state.get("generated_code", ""),
                "captured_output": state.get("captured_output", ""),
                "error": str(crit_err)
            }
            
        except Exception as e:
            logger.error(f"Unexpected Pipeline execution crash: {str(e)}", exc_info=True)
            return {
                "status": "fatal",
                "insights_summary": None,
                "generated_code": None,
                "captured_output": None,
                "error": "Internal Orchestration Error"
            }

    async def _run_agent(self, agent, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes an agent with retry. Merges the agent's returned dict
        directly into the shared state so downstream agents can read keys flat.
        """
        max_retries = settings.MAX_RETRIES
        attempts = 0
        agent_name = agent.__class__.__name__
        
        while attempts < max_retries:
            try:
                logger.info(f"Dispatching task to [ {agent_name} ] (Attempt {attempts + 1}/{max_retries})")
                
                result = await agent.process(state)
                
                # CRITICAL: Merge the result dict directly into state
                # so that e.g. {"generated_code": "..."} becomes state["generated_code"]
                if isinstance(result, dict):
                    state.update(result)
                
                logger.info(f"[ {agent_name} ] completed successfully.")
                return state
                
            except Exception as e:
                attempts += 1
                logger.warning(f"Error caught inside [ {agent_name} ]: {str(e)}. Retrying...")
                
                if attempts >= max_retries:
                    logger.error(f"[ {agent_name} ] critically failed after {max_retries} attempts.")
                    raise RuntimeError(f"{agent_name} failed definitively: {str(e)}")
                    
        return state
