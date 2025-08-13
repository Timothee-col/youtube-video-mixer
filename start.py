import os
import subprocess

# Get port from environment
port = int(os.environ.get('PORT', 8501))

# Run streamlit
cmd = [
    'streamlit', 
    'run', 
    'upload_video_mixer.py',
    '--server.port=' + str(port),
    '--server.address=0.0.0.0',
    '--server.headless=true'
]

print(f"Starting on port {port}")
print(f"Command: {' '.join(cmd)}")

subprocess.run(cmd)
