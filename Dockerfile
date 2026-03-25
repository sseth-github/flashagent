# Use the official Python slim image as the base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a data directory
RUN mkdir -p /app/data

# Copy the rest of the application code into the container
COPY . .

# Command to run the application
CMD ["python", "app.py"]
