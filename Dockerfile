# Start from the official Python image
FROM python:3.9

# Set the working directory
WORKDIR /code

# Copy requirements first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt

# Install system dependencies for Scrapy and Python dependencies
RUN apt-get update && \
    apt-get install -y gcc libxml2-dev libxslt1-dev libz-dev libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# Copy application code
COPY ./app /code/app
COPY ./start.sh /code/start.sh

# Make the start script executable
RUN chmod +x /code/start.sh

# Expose necessary ports
EXPOSE 80
EXPOSE 2222

# Set entrypoint
ENTRYPOINT ["/code/start.sh"]
