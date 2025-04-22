#!/bin/bash

# Delete MP4 files older than 30 days from the recordings directory
find /recordings -name "*.mp4" -type f -mtime +30 -delete 