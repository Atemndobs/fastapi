# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import quiz, apartment

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

# Include routers
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])
app.include_router(apartment.router, prefix="/api/v1/apartment", tags=["apartment"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"status": "healthy"}
