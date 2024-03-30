from typing import Union
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from litellm import completion
import os
import pandas as pd
from pydantic import BaseModel
from . import songs  # adjust the import based on your folder structure
from . import quiz
from . import diagram
# from . import crew
# from . import gradio
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, HTTPException
import httpx
import logging
import colorlog

from fastapi import APIRouter, HTTPException, Query, Request
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.database import ElastiCache, RDS
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, Route53, VPC
from diagrams.aws.security import WAF
from diagrams.aws.storage import S3
from diagrams.aws.database import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3
import importlib.util

# GCP IMORTS
from diagrams.gcp.analytics import BigQuery, Dataflow, PubSub
from diagrams.gcp.compute import AppEngine, Functions
from diagrams.gcp.database import BigTable
from diagrams.gcp.iot import IotCore
from diagrams.gcp.storage import GCS


# On Pre Imports
from diagrams.onprem.analytics import Spark
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.aggregator import Fluentd
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import Kafka

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
app.include_router(diagram.router, prefix="/api/v1/diagram", tags=["diagram"])
# app.include_router(crew.router, prefix="/api/v1/crew", tags=["crew"])


current_file_path = os.path.dirname(__file__)
diagrams_path = os.path.join(current_file_path, "diagrams")

app.mount("/diagrams", StaticFiles(directory=diagrams_path), name="diagrams")



@app.get("/health")
def health_check():
    return {"status": "healthy"}



@app.get("/")
def health_check():
    return {"status": "healthy"}


#app.include_router(gradio.router, prefix="/api/v1", tags=["gradio"])
