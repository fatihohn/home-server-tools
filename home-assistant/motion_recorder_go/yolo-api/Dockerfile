FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install uv && \
    uv venv && \
    uv pip install flask opencv-python-headless ultralytics

RUN apt-get update && \
    apt-get install -y ffmpeg cron && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "app.py"]
