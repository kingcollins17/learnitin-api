FROM python:3.13-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for mysqlclient or other libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Use fastapi run as requested
CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8080"]
