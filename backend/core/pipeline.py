import logging
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

def step_logging_wrapper(func: Callable) -> Callable:
    """
    Decorator providing a standard logging wrapper around any pipeline step.
    Monitors execution times and guarantees clean telemetry trails formatting.
    """
    @wraps(func)
    async def wrapper(self, state: Dict[str, Any], *args, **kwargs) -> Any:
        step_name = getattr(self, 'step_name', self.__class__.__name__)
        logger.info(f"➤ [START] Executing pipeline step: {step_name}")
        
        start_time = time.time()
        try:
            # Await the actual process method block
            result = await func(self, state, *args, **kwargs)
            
            elapsed = time.time() - start_time
            logger.info(f"✔ [SUCCESS] {step_name} completed in {elapsed:.3f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"✖ [FAILED] {step_name} crashed after {elapsed:.3f}s. Exception: {str(e)}")
            # Re-raise to let the orchestrator's retry logic catch it
            raise

    return wrapper


class PipelineStep(ABC):
    """
    Abstract Base Class for all Autonomous Agents and Orchestrator steps.
    Enforces a strict modular contract: every subclass must implement `process()`.
    """
    
    @property
    def step_name(self) -> str:
        """
        Hook to allow agents to provide custom naming in the logs.
        Defaults to the native Class name.
        """
        return self.__class__.__name__

    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Any:
        """
        The core execution loop of the module.
        
        Args:
            state (Dict[str, Any]): The shared contextual dictionary passed sequentially through the Pipeline.
            
        Returns:
            Any: The specific dictionary delta block (or object) produced by this agent,
                 which is safely merged back into the state inside the Orchestrator.
        """
        pass
