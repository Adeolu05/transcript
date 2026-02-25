import logging
import sys

def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Optional: silence noisy loggers from third-party libraries here
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return logging.getLogger("transcript_flow")

logger = setup_logging()
