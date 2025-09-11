FROM ubuntu:22.04

# Install Python 3 and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Scapy
RUN pip3 install scapy

# Copy and run the script
COPY sender.py /app/sender.py

WORKDIR /app
CMD ["python3", "sender.py"]