#!/usr/bin/env python3
"""
Script de démarrage pour Railway
Gère le port dynamique fourni par Railway
"""
import os
import sys
import subprocess

# Récupérer le port depuis l'environnement Railway
port = os.environ.get('PORT', '8501')

# Commande Streamlit avec le port
cmd = [
    'streamlit', 'run', 'upload_video_mixer.py',
    '--server.port', port,
    '--server.address', '0.0.0.0',
    '--server.headless', 'true',
    '--browser.gatherUsageStats', 'false'
]

print(f"🚀 Démarrage sur le port {port}...")
print(f"Commande: {' '.join(cmd)}")

# Lancer Streamlit
subprocess.run(cmd)
