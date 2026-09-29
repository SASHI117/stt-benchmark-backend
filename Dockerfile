FROM python:3.11-slim

# libasound2/libssl are needed at runtime by the Azure Speech SDK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libasound2 libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
