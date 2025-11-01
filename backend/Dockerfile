FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install Playwright browsers for Crawl4AI
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Copy application code
COPY . .

# Expose port (Railway will inject PORT env variable)
EXPOSE 8080

# Run application - use PORT env variable (Railway/Render compatible)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
