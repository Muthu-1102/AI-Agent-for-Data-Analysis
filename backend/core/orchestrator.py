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
            "errors": []
        }
        
        try:
            # Step 1: SchemaAgent → extracts columns, dtypes, sample_rows
            state = await self._run_agent(self.schema_agent, state)
            
            # Step 2: PromptAgent → builds structured_prompt
            state = await self._run_agent(self.prompt_agent, state)
            
            # Step 3: CodeAgent → produces generated_code, raw_llm_response
            state = await self._run_agent(self.code_agent, state)
            
            # Step 4: ValidationAgent → validation_passed, validation_message
            state = await self._run_agent(self.validation_agent, state)
            
            # Step 5: ExecutionAgent → execution_success, captured_output, error_trace
            state = await self._run_agent(self.execution_agent, state)
            
            # Step 6: ReportAgent → insights_summary, report_generated
            state = await self._run_agent(self.report_agent, state)
            
            logger.info(f"Pipeline successfully completed for query: '{query}'")
            return {
                "status": "completed",
                "insights_summary": state.get("insights_summary", ""),
                "generated_code": state.get("generated_code", ""),
                "captured_output": state.get("captured_output", ""),
                "error": None
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
