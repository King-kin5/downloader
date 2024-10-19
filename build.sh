#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y ffmpeg python3-pip wget unzip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Google Chrome
echo "Installing Google Chrome..."
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome.deb || apt-get install -y -f  # Fix dependencies if needed
rm google-chrome.deb

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -q https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d ./chromedriver
rm chromedriver_linux64.zip

# Move ChromeDriver to a writable directory
mv ./chromedriver/chromedriver ./chromedriver/chromedriver
chmod +x ./chromedriver/chromedriver

# Display installed versions
echo "Installed versions:"
./chromedriver/chromedriver --version
google-chrome --version
