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
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical packages are installed
RUN pip show gunicorn || pip install gunicorn==21.2.0
RUN pip show playwright || pip install playwright>=1.40.0

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Expose port (Railway will inject PORT env variable)
EXPOSE 8080

# Run application - use PORT env variable (Railway/Render compatible)
# Use shell form to allow environment variable expansion
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120 app:app"]
