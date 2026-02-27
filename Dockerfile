FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set default Environment Variables
ENV DOWNLOAD_DIR=/downloads
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ ./templates/

# Create the downloads directory
RUN mkdir -p /downloads

# Standard Flask port
EXPOSE 5000

CMD ["python", "app.py"]