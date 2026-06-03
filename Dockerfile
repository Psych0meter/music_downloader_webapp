FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV DOWNLOAD_DIR=/downloads \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Install dependencies first (layer-cached until requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app.py .
COPY providers/ ./providers/
COPY templates/ ./templates/

# Persistent download volume mount point
RUN mkdir -p /downloads

# Expose Flask port
EXPOSE 5000

# Lightweight health check — uses the /api/health endpoint added in app.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

CMD ["python", "app.py"]
