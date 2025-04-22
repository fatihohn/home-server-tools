#!/bin/bash

# Set up cron job to run cleanup daily at 2 AM
echo "0 2 * * * /app/cleanup.sh" > /etc/cron.d/cleanup
chmod 0644 /etc/cron.d/cleanup

# Start cron service
service cron start

# 프로그램 실행
python main.py