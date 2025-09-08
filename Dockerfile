# Use Python 3.12.11 Alpine image
FROM python:3.12.11-alpine3.22

# Set working directory
WORKDIR /app

# Install system dependencies for Alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create non-root user for security
RUN adduser -D -s /bin/sh app \
    && chown -R app:app /app
USER app

# Run the application
CMD ["python", "main.py"]
