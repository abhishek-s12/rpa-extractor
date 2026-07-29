"""Logging setup for the Ren'Py Asset Extraction Tool using Loguru.

Logs are piped to both stderr and a rotating file inside the 'logs' folder.
"""

import sys
from pathlib import Path
from loguru import logger

# Output log directory
if getattr(sys, "frozen", False):
    LOG_DIR = Path(sys.executable).resolve().parent / "logs"
else:
    LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Format specifications
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger(debug: bool = False) -> None:
    """Configures the loguru logger handlers.

    Args:
        debug: If True, enables debug-level logging.
    """
    # Remove existing default handler
    logger.remove()

    # Determine log level
    log_level = "DEBUG" if debug else "INFO"

    # Add console handler
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            format=LOG_FORMAT,
            level=log_level,
            colorize=True,
        )

    # Add rotating file handler
    logger.add(
        LOG_DIR / "app.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # Always log everything to files for debugging
        rotation="10 MB",
        retention="5 days",
        compression="zip",
    )

    logger.info(f"Logger initialized. Logs are stored in: {LOG_DIR / 'app.log'}")
