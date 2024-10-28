from typing import Union
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import colorlog

from . import quiz  # Only keeping the quiz module

app = FastAPI()

# List of allowed origins
origins = [
    "http://localhost",
    "http://mage.tech",
    "127.0.0.1",
    "0.0.0.0",
    "agile.atemkeng.de",
    "n8n.atemkeng.de",
    "*"
]

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only the quiz router
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"status": "healthy"}
