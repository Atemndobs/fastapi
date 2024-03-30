from fastapi import FastAPI, APIRouter, HTTPException
from crewai import Crew, Agent, Task
import logging
import colorlog

from dotenv import load_dotenv
import os

load_dotenv()  # This will load the .env file

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    }
)
