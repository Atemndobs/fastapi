#!/bin/bash
# Start Uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 80 --reload --log-level debug
