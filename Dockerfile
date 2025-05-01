# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OSMnx
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for cache and analyses
RUN mkdir -p cache analyses

# Expose port 3000
EXPOSE 3000

# Run the application
CMD ["python3", "app.py"] 