#!/bin/bash
# Setup script for Streamlit Cloud
echo "Setting up YouTube Video Mixer..."

# Ensure pip is up to date
pip install --upgrade pip setuptools wheel

# Install cmake first
pip install cmake==3.27.7

# Install numpy with specific version
pip install numpy==1.24.3

# Install dlib with compilation flags
CFLAGS="-O3" pip install dlib==19.24.2 --no-cache-dir

# Install face-recognition
pip install face-recognition==1.3.0

echo "Setup complete!"
