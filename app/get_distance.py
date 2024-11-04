from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
# from dotenv import load_dotenv
from .models import DistanceRequest, DistanceResponse
from .utils import get_distance_data

router = APIRouter()

@router.post("/get_distance", response_model=DistanceResponse)
async def get_distance(distance_request: DistanceRequest):
    return get_distance_data(distance_request)