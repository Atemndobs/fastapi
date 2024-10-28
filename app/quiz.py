from fastapi import APIRouter, HTTPException, Query
import httpx
from typing import Union
from fastapi import FastAPI, HTTPException

import os
import pandas as pd
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
router = APIRouter()

# Load the CSV data into a DataFrame
df = pd.read_csv("/code/app/quiz_data.csv")

@router.get("/")
def read_root():
    return {"Hello": "World"}


@router.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@router.get("/questions/{question_id}")
def get_question(question_id: int):
    """Fetch a specific question and its choices."""
    start_idx = (question_id - 1) * 4
    end_idx = start_idx + 4
    if start_idx >= len(df):
        raise HTTPException(status_code=404, detail="Question not found")
    question_data = df.iloc[start_idx:end_idx]

    # Create a link for the next question
    next_question_id = question_id + 1
    # Check if there's a next question
    next_start_idx = (next_question_id - 1) * 4
    if next_start_idx >= len(df):
        # No more questions
        next_question_link = None
    else:
        next_question_link = f"/questions/{next_question_id}"

    # Create a link for the previous question
    prev_question_id = question_id - 1
    if prev_question_id <= 0:
        # No previous questions
        prev_question_link = None
    else:
        prev_question_link = f"/questions/{prev_question_id}"

    return {
        "question": question_data["Question"].iloc[0],
        "choices": question_data["Choices"].tolist(),
        "next_question_link": next_question_link,
        "prev_question_link": prev_question_link  # Add this line
    }


class Answer(BaseModel):
    answer: int

@router.post("/validate_answer/{question_id}")
def validate_answer(question_id: int, answer: Answer):
    """Validate the provided answer for a specific question."""
    start_idx = (question_id - 1) * 4
    if start_idx + answer.answer >= len(df):
        raise HTTPException(status_code=404, detail="Invalid choice")
    is_correct = bool(df.iloc[start_idx + answer.answer]["Answer"] == 1)
    return {"is_correct": is_correct}
