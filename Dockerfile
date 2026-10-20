FROM python:3.9-slim

# Install FFmpeg for audio processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install python dependencies
RUN pip install --no-cache-dir flask flask-cors

EXPOSE 5000
CMD ["python", "service.py"]
