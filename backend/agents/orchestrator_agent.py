from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper
from core.orchestrator import Orchestrator

class OrchestratorAgent(PipelineStep):
    """
    Agent wrapper for the core Orchestrator pipeline logic.
    
    This encapsulation allows the entire Data Analysis multi-agent system to be 
    treated as a single composable 'Step' (Meta-Agent). This is highly beneficial 
    if you want to trigger this pipeline inside a broader company-wide system.
    """
    
    def __init__(self):
        super().__init__()
        # Instantiate the inner core Orchestrator engine
        self._orchestrator = Orchestrator()
        
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the main Orchestrator pipeline natively through the PipelineStep interface.
        
        Args:
            state (Dict[str, Any]): The initial parameters containing at minimum 'query' and 'file_id'.
            
        Returns:
            Dict[str, Any]: A mapping containing the aggregate orchestrator output block.
        """
        query = state.get("query")
        file_id = state.get("file_id")
        
        if not query or not file_id:
            raise ValueError("OrchestratorAgent requires 'query' and 'file_id' within the current state context.")
            
        # Delegate directly into the Core Orchestrator logic
        result = await self._orchestrator.execute_pipeline(query=query, file_id=file_id)
        
        return {
            "status": "completed",
            "aggregate_result": result
        }
