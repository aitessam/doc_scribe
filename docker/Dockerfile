FROM python:3.11-slim

# System dependencies (PortAudio for sounddevice)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        portaudio19-dev \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]

