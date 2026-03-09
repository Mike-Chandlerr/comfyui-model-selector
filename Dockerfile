FROM python:3.12-slim

# Install wget for downloads
RUN apt-get update && apt-get install -y wget curl && rm -rf /var/lib/apt/lists/*

# Install Flask
RUN pip install --no-cache-dir flask

WORKDIR /app

# Copy application files
COPY app.py .
COPY models.json .
COPY templates/ templates/

# Create data directory for persistent user models
RUN mkdir -p /app/data

# Default env vars
ENV COMFY_ROOT=/comfyui-models
ENV MODELS_JSON=/app/models.json
ENV USER_MODELS_JSON=/app/data/user_models.json
ENV DATA_DIR=/app/data
ENV PORT=5000
ENV MAX_CONCURRENT_DOWNLOADS=2

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

CMD ["python", "app.py"]
