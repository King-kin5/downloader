#!/usr/bin/env bash
# Install system dependencies
apt-get update
apt-get install -y ffmpeg python3-pip

# Install Python dependencies
pip install -r requirements.txt

# Install Google Chrome
echo "Installing Google Chrome..."
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome.deb
rm google-chrome.deb

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -q https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d ./chromedriver  # Extract to a writable directory
rm chromedriver_linux64.zip

# Move ChromeDriver to a writable directory and set permissions
mv ./chromedriver/chromedriver /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver

# Display installed versions
google-chrome --version
chromedriver --version
