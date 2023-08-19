from typing import Union
from fastapi import FastAPI, HTTPException
from litellm import completion
import os
import pandas as pd
from pydantic import BaseModel

app = FastAPI()

# Load the CSV data into a DataFrame
df = pd.read_csv("/code/app/quiz_data.csv")

@app.get("/questions/{question_id}")
def get_question(question_id: int):
    """Fetch a specific question and its choices."""
    start_idx = (question_id - 1) * 4
    end_idx = start_idx + 4
    if start_idx >= len(df):
        raise HTTPException(status_code=404, detail="Question not found")
    question_data = df.iloc[start_idx:end_idx]
    return {
        "question": question_data["Question"].iloc[0],
        "choices": question_data["Choices"].tolist()
    }

class Answer(BaseModel):
    answer: int

@app.post("/validate_answer/{question_id}")
def validate_answer(question_id: int, answer: Answer):
    """Validate the provided answer for a specific question."""
    start_idx = (question_id - 1) * 4
    if start_idx + answer.answer >= len(df):
        raise HTTPException(status_code=404, detail="Invalid choice")
    is_correct = bool(df.iloc[start_idx + answer.answer]["Answer"] == 1)
    return {"is_correct": is_correct}
