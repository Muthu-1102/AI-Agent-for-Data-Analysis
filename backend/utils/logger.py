import logging
import os
import sys

def setup_logging(name="api"):
    """
    Configures and returns a centralized logger with both Console and File handlers.
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicating logs if setup multiple times
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    
    # Ensure logs directory exists alongside backend
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, "system.log")

    # Clean standardized log string format
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (Standard Output for Dev Mode)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Persistent Log File)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Create the singleton logger that can be directly imported
logger = setup_logging()

def log_llm_interaction(prompt: str, response: str, model: str):
    """
    Specific logging struct for isolating and tracing raw LLM traffic.
    """
    logger.info("=== 🧠 LLM INTERACTION START ===")
    logger.info(f"Model: {model}")
    logger.info(f"--- Prompt Sent ---\n{prompt}\n")
    logger.info(f"--- Response Received ---\n{response}\n")
    logger.info("=== 🧠 LLM INTERACTION END ===")
    
def log_step(agent_name: str, status: str, details: str = ""):
    """
    Step-based execution log telemetry.
    """
    msg = f"[{agent_name}] -> {status}"
    if details:
        msg += f" | {details}"
    logger.info(msg)
