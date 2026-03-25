# Upgrade to 3.12 for better compatibility and fewer warnings
FROM python:3.12-slim

WORKDIR /app

# Crucial: This tells Python to look in the root for constants.py
ENV PYTHONPATH="/app"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the data directory exists for your logs/db
RUN mkdir -p /app/data

COPY . .

# Use the full path for the command
CMD ["python", "src/main.py"]
