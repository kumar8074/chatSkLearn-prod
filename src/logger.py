# ===================================================================================
# Project: ChatSkLearn
# File: src/logger.py
# Description: Logging setup script
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

"""This script sets up a logging configuration for the project.

It creates a directory for logs if it doesn't exist and configures the
logging format and level. The log file is named with the current date and time.
The logging messages include the timestamp, line number, logger name, log level,
and the actual log message.
"""

import logging
import os
import sys
from datetime import datetime

# Log file with timestamp
LOG_FILENAME = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

# Correct log path for Docker
LOGS_DIR = os.path.join(os.getcwd(), "logs")  # ✅ not app/logs
os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOGS_DIR, LOG_FILENAME)

# Define format
LOG_FORMAT = "[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s"

# Create handlers
file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)

# Set same formatter
formatter = logging.Formatter(LOG_FORMAT)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Root logger config
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)


