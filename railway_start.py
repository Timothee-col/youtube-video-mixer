#!/usr/bin/env python3
"""
Script de démarrage pour Railway qui gère correctement le port dynamique
"""
import os
import subprocess
import sys

def main():
    # Récupérer le port de Railway (défaut 8501)
    port = os.environ.get('PORT', '8501')
    
    print(f"🚀 Démarrage Railway sur le port: {port}")
    print(f"🌐 URL attendue: https://votre-app.railway.app")
    
    # Commande Streamlit avec le port correct
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'upload_video_mixer.py',
        '--server.port', str(port),
        '--server.address', '0.0.0.0',
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false'
    ]
    
    print(f"📡 Commande: {' '.join(cmd)}")
    
    # Lancer Streamlit
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()