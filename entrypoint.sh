#!/bin/bash

# Start cron daemon
echo "Starting cron daemon..."
cron

# Run the script once on startup (optional)
if [ "${RUN_ON_STARTUP}" = "true" ]; then
    echo "Running initial sync on startup..."
    /usr/local/bin/python plex_to_arr.py
fi

# Keep container running and tail logs
echo "Container started. Sync scheduled every hour."
echo "Logs will be available in /app/logs/sync.log"
echo "Cache file: /app/logs/sync_cache.json"
echo "Current time: $(date)"

# Create initial log file if it doesn't exist
touch /app/logs/sync.log

# Keep container alive and show logs
tail -f /app/logs/sync.log