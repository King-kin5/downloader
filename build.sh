#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download Chromium (headless version of Chrome)
echo "Downloading Chromium..."
wget -q https://download-chromium.appspot.com/dl/Linux_x64?type=snapshots -O chromium.zip
unzip chromium.zip -d ./chromium
rm chromium.zip

# Download ChromeDriver
echo "Downloading ChromeDriver..."
CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -q https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d ./chromedriver
rm chromedriver_linux64.zip

# Move ChromeDriver to a writable directory
chmod +x ./chromedriver/chromedriver

# Display installed versions
echo "Installed versions:"
./chromedriver/chromedriver --version
