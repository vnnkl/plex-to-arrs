FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY plex_to_arr.py .
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create log directory
RUN mkdir -p /app/logs

# Set up cron job for hourly execution
RUN echo "0 * * * * cd /app && python plex_to_arr.py >> /app/logs/sync.log 2>&1" | crontab -

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]