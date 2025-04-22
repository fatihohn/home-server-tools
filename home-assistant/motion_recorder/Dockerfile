FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install uv && \
    uv venv && \
    uv pip install python-dotenv opencv-python-headless

RUN apt-get update && \
    apt-get install -y ffmpeg cron && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    chmod +x /app/cleanup.sh && \
    chmod +x /app/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

CMD ["/app/docker-entrypoint.sh"]
