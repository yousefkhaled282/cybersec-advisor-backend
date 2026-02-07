FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for local fallback
RUN mkdir -p data

# Environment variables for Cloud Run
ENV PORT=8080

# Run command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]