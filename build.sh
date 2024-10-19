#!/usr/bin/env bash
# Install system dependencies
apt-get update
apt-get install -y ffmpeg python3-pip

# Install Python dependencies
pip install -r requirements.txt

# Install Chrome
echo "Installing Google Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d /tmp/
mv /tmp/chromedriver /opt/chromedriver || echo "Failed to move ChromeDriver"
rm chromedriver_linux64.zip

# Ensure ChromeDriver has execute permissions
chmod +x /opt/chromedriver || echo "Failed to set execute permissions"

# Add ChromeDriver to PATH
export PATH=$PATH:/opt

# Display installed versions
google-chrome --version || echo "Google Chrome not found"
chromedriver --version || echo "ChromeDriver not found"
