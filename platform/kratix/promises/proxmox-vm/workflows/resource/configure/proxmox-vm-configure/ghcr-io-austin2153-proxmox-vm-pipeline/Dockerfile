FROM python:3.12-slim

RUN python -m pip install kratix-sdk requests urllib3

WORKDIR /app
COPY scripts/pipeline.py /app/pipeline.py

ENTRYPOINT ["python", "-u", "/app/pipeline.py"]