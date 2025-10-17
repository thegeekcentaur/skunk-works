FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    default-jre \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Copy app code
COPY app app

# Copy samples folder
COPY samples samples

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set workdir
WORKDIR /app

# Create output directory for generated packages
RUN mkdir -p /app/output

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
