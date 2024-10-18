#!/usr/bin/env bash
# Install system dependencies
apt-get update
apt-get install -y ffmpeg python3-pip

# Install Python dependencies
pip install -r requirements.txt