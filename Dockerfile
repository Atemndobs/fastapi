#
FROM python:3.9

#
WORKDIR /code

#
COPY ./requirements.txt /code/requirements.txt

#
RUN pip install --upgrade pip
RUN pip install scikit-learn  # for sklearn
RUN pip install colorlog  # for colorlog
# Install Graphviz and its development libraries
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# run autogenstudio ui

#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
# Copy the start script into the container
COPY ./start.sh /code/start.sh

# Make the start script executable
RUN chmod +x /code/start.sh

# Expose the port that FastAPI runs on
EXPOSE 80
EXPOSE 8081
EXPOSE 8085
EXPOSE 1234


# Use the start script as the entry point
ENTRYPOINT ["/code/start.sh"]
