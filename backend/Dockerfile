# Use official Python base image
FROM python:3.10-slim

# Install system dependencies for moviepy/ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements from backend folder
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the backend folder into the container
COPY backend/ .

# Final start command is managed by railway.json
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
