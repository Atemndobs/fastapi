# Use the official Python image as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file into the container
COPY ./requirements.txt /code/requirements.txt

# Install and upgrade pip, then install dependencies from requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy the app directory and start script into the container
COPY ./app /code/app
COPY ./start.sh /code/start.sh

# Make the start script executable
RUN chmod +x /code/start.sh

# Expose only the necessary port for FastAPI (usually 80 or 8000 by convention)
EXPOSE 80

# Set the start script as the entry point
ENTRYPOINT ["/code/start.sh"]
