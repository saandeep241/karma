FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/tasks data/reasoning data/memory

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
EXPOSE 8080

# Run the application
# Cloud Run sets PORT environment variable, use it or default to 8000 for local dev
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

