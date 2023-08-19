from typing import Union
from fastapi import FastAPI, HTTPException
from litellm import completion
import os

app = FastAPI()



 # Set ENV variables (preferably, do this outside of the app)
os.environ["OPENAI_API_KEY"] = "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"
os.environ["COHERE_API_KEY"] = "cohere key"


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/ai")
async def generate_response(messages: list):
 # Ensure the messages input is valid
 if not messages or not isinstance(messages, list):
     raise HTTPException(status_code=400, detail="Invalid messages input")

 # openai call
 openai_response = completion(model="gpt-3.5-turbo", messages=messages)

 # cohere call
 # cohere_response = completion("command-nightly", messages)

 return {
     "openai_response": openai_response,
     #  "cohere_response": cohere_response
 }


