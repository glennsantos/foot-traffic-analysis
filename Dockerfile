# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OSMnx with retry logic
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/80-retries && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY . .

# Create directories for cache and analyses with correct permissions
RUN mkdir -p cache analyses_new reports /app/.matplotlib_cache && \
    chmod 777 analyses_new reports /app/.matplotlib_cache

# Expose the application port
EXPOSE 1010

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=1010
ENV PORT=1010
ENV MPLCONFIGDIR=/app/.matplotlib_cache

# Run the application
CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS:-2} -t ${GUNICORN_TIMEOUT:-300} -k sync -b 0.0.0.0:${PORT:-1010} app:app"]
