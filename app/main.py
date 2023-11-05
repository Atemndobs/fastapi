from typing import Union
from fastapi import FastAPI, HTTPException
from litellm import completion
import os
import pandas as pd
from pydantic import BaseModel
from . import songs  # adjust the import based on your folder structure
from . import quiz
# from . import gradio
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter()
app = FastAPI()

# List of allowed origins
origins = [
    "http://localhost",        # For local development
    "http://mage.tech",
    "127.0.0.1",
    "0.0.0.0"
    "agile.atmkeng.de",
    "*"# If it's hosted on this domain
]

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "accept"],
)

app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])

app.include_router(songs.router, prefix="/api/v1/songs", tags=["songs"])

#app.include_router(gradio.router, prefix="/api/v1", tags=["gradio"])
