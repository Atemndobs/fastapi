#!/bin/bash

# Start AutogenStudio UI in the background
autogenstudio ui --host 0.0.0.0 --port 8081 &

# Start Uvicorn server

uvicorn app.main:app --host 0.0.0.0 --port 80
