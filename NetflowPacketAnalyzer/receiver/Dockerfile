# Dockerfile.receiver - Multi-stage build
FROM rust:1.75-slim as rust-builder

# Install dependencies for Rust compilation
RUN apt-get update && apt-get install -y   \
    pkg-config   \
    libssl-dev   \
    python3-dev   \
    python3-pip   \
    python3-venv   \
    build-essential   \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install maturin
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install maturin

# Set working directory for Rust build
WORKDIR /rust_build

# Copy Rust source files
COPY rust_processor/ ./

# Clean any existing builds
RUN cargo clean || true

# Build the Python extension module with maturin
ENV PATH="/opt/venv/bin:$PATH"
RUN maturin build --release --out dist --find-interpreter

# Verify the wheel was built
RUN ls -la dist/

# Python runtime stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y   \
    ca-certificates   \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python application
COPY receiver.py .

# Copy the built wheel from rust-builder stage
COPY --from=rust-builder /rust_build/dist/*.whl /tmp/

# Install the Rust Python module
RUN pip install /tmp/*.whl

# Test the module import
RUN python -c "import netflow_processor; print('netflow_processor module installed successfully')" ||   \
    echo "netflow_processor module installation failed - use Python fallback"

# Expose the netflow port
EXPOSE 2055/udp

# Set environment variables
ENV RUST_LOG=info
ENV LISTEN_HOST=0.0.0.0
ENV LISTEN_PORT=2055
ENV DEMO_RUST=false

# Run the Python receiver
CMD ["python", "receiver.py"]