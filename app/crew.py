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


# Now you can access the API key with os.getenv
# openai_api_key = os.getenv("OPENAI_API_KEY")
# logger.info("OPENAI_API_KEY: %s", openai_api_key)


# Define your agents and tasks with appropriate checks and logging
# try:
#     logger.info("Defining agents and tasks")
#
#     researcher = Agent(
#         role='Researcher',
#         goal='Perform research',
#         backstory='A skilled researcher with expertise in data analysis.',
#         verbose=True,
#         allow_delegation=False,
#         # Add tools and other configurations as required
#     )
#
#     writer = Agent(
#         role='Writer',
#         goal='Write articles',
#         backstory='An experienced writer with a focus on technical topics.',
#         verbose=True,
#         allow_delegation=True,
#         # Add tools and other configurations as required
#     )
#
#     task1 = Task(
#         description='Research task description',
#         agent=researcher
#     )
#
#     task2 = Task(
#         description='Writing task description',
#         agent=writer
#     )
#
# except Exception as e:
#     logger.error("Error in defining agents or tasks: %s", str(e))
#     raise HTTPException(status_code=500, detail="Error in setting up agents or tasks")
#
# # Set up FastAPI router
# router = APIRouter()
#
# @router.get("/run_analysis")
# async def run_analysis():
#     try:
#         logger.info("Starting analysis in /run_analysis endpoint")
#         crew = Crew(
#             agents=[researcher, writer],
#             tasks=[task1, task2],
#             verbose=2,
#         )
#         result = crew.kickoff()
#         return {"result": result}
#     except Exception as e:
#         logger.error("Error in /run_analysis endpoint: %s", str(e))
#         raise HTTPException(status_code=500, detail="Error in /run_analysis endpoint")
#
# # Create FastAPI app instance and include the router
# app = FastAPI()
# app.include_router(router)
