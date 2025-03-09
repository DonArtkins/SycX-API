# Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK 'punkt' resource
RUN python -m nltk.downloader punkt

# Copy application code
COPY . .

# Set environment variables to help with memory
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=4
ENV PYTHONUNBUFFERED=1

# Expose the port Render will use
EXPOSE $PORT

# Use gunicorn with explicit configuration
CMD gunicorn \
    --workers $GUNICORN_WORKERS \
    --threads $GUNICORN_THREADS \
    --timeout 120 \
    --bind 0.0.0.0:$PORT \
    app:app