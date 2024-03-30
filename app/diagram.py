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

import runpy

import logging
import colorlog
import os



# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set format for the logger
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

# Create a console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

router = APIRouter()

@router.get("/create")
def create_diagram(request: Request, q: str = Query(..., description="The name of the file to be created"), format: str = Query("png", description="The format of the diagram")):
    filename = q
    # if format is None: the set the default format to png
    if format is None:
        format = "png"

    # Diagram Code Directory
    diagram_code_dir = os.path.join(os.path.dirname(__file__), "diagram_code")
    os.makedirs(diagram_code_dir, exist_ok=True)  # Ensure the directory exists
    diagram_code_path = os.path.join(diagram_code_dir, f"{filename}.py")

    # diagram Output Directory
    diagram_dir = os.path.join(os.path.dirname(__file__), "diagrams")
    diagram_path = os.path.join(diagram_dir, f"{filename}.{format}")

    try:
        base_url = str(request.base_url)
        diagram_url = f"{base_url}diagrams/{filename}.{format}"
        logger.info("Diagram creation started. $$$")
        spec = importlib.util.spec_from_file_location("diagram_module", diagram_code_path)
        diagram_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagram_module)
        try:
            logging.info(f"======= diagram_code_path: {diagram_code_path}")
            # spec.loader.exec_module(diagram_module)
            runpy.run_path(diagram_code_path)
        except Exception as e:
            logger.error(f"Code Execution ERROR {e}")
            raise HTTPException(status_code=500, detail= {
                "message": "Code Execution ERROR.",
                "error": f"{e}"
            })


        # Call a function from the imported module and pass parameters
        if hasattr(diagram_module, 'create_diagram'):
             diagram_module.create_diagram(filename, diagram_dir)
#         if not os.path.exists(diagram_path):
#             raise HTTPException(status_code=404, detail= {
#                 "message": "Diagram was not created Please check send the code again",
#                 "create_from_payload": f"{base_url}api/v1/diagram/create_from_payload"
#             } )

        logger.info(f"Diagram created successfully. from {filename}")
        return {
            "message": f"Diagram created successfully from {filename}.",
            "file_path": diagram_path,
            "url": diagram_url
        }
    except Exception as e:
        logger.error(f"An error occurred while creating the diagram: {e}")
        raise HTTPException(status_code=500, detail= {
            "message": "An error occurred while creating the diagram.",
            "error": f"{e}"
        })


@router.post("/create_from_payload")
async def create_diagram_from_payload(request: Request, payload: dict):
    diagram_code = payload.get("diagram_code")
    filename = payload.get("filename", "default_diagram")

    if not diagram_code or not filename:
        raise HTTPException(status_code=400, detail="Both diagram code and filename are required")

    diagram_dir = os.path.join(os.path.dirname(__file__), "diagrams")
    logging.info(f"diagram_dir: {diagram_dir}")
    os.makedirs(diagram_dir, exist_ok=True)
    diagram_path = os.path.join(diagram_dir, f"{filename}.{format}")
    logger.info(f"diagram_code: {diagram_code}")
    # write content to a file name filename.py in the diagram_code folder
    diagram_code_dir = os.path.join(os.path.dirname(__file__), "diagram_code")
    os.makedirs(diagram_code_dir, exist_ok=True)
    diagram_code_path = os.path.join(diagram_code_dir, f"{filename}.py")
    with open(diagram_code_path, "w") as f:
        f.write(diagram_code)
    # change file permission to 777
    os.chmod(diagram_code_path, 777)

    try:
        logger.info("Diagram creation started.")
        spec = importlib.util.spec_from_file_location("diagram_module", diagram_code_path)
        diagram_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagram_module)
        # Call a function from the imported module and pass parameters
        if hasattr(diagram_module, 'create_diagram'):
             diagram_module.create_diagram(filename, diagram_dir)
        if not os.path.exists(diagram_path):
            raise HTTPException(status_code=404, detail= {
                "message": "Diagram was not created Please check send the code again"
            } )


        logger.info("Diagram created successfully.")
        base_url = str(request.base_url)
        diagram_url = f"{base_url}diagrams/{filename}.{format}"
        # check if the file exists
        if not os.path.exists(diagram_path):
            raise HTTPException(status_code=404, detail= {
                "message": "Diagram was not created Please recheck the diagram code"
            } )

        logger.info("Diagram created successfully from payload.")
        return {
            "message": "Diagram created successfully from payload.",
            "file_path": diagram_path,
            "url": diagram_url
        }
    except Exception as e:
        logger.error(f"An error occurred while creating the diagram: {e}")
        raise HTTPException(status_code=500, detail= {
            "message": "An error occurred while creating the diagram.",
            "error": f"{e}"
        })


#     try:
#         logger.info("Diagram creation from payload started.")
#
#         # Dynamically execute the received diagram code
#         exec(diagram_code, {'__builtins__': __builtins__})
#
#
#         # Construct the URL dynamically based on the request's base URL
#         base_url = str(request.base_url)
#         diagram_url = f"{base_url}diagrams/{filename}.png"
#
#         logger.info("Diagram created successfully from payload.")
#         return {
#             "message": "Diagram created successfully from payload.",
#             "file_path": diagram_path,
#             "url": diagram_url
#         }
#     except Exception as e:
#         logger.error(f"An error occurred while creating the diagram from payload: {e}")
#         raise HTTPException(status_code=500, detail=str(e))