#!/usr/bin/env bash
# Install system dependencies
apt-get update
apt-get install -y ffmpeg python3-pip

# Install Python dependencies
pip install -r requirements.txt

# Create properly formatted cookies file
cat > cookies.txt << EOL
# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	FALSE	2597573456	CONSENT	YES+cb
EOL

chmod 666 cookies.txt