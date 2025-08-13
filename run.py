#!/usr/bin/env python3
"""
Script de démarrage pour Railway - Gestion du port dynamique
"""
import os
import sys

# Obtenir le port depuis l'environnement (Railway le fournit)
port = os.environ.get('PORT', '8501')
print(f"🚀 Démarrage de l'application sur le port {port}")

# Configurer Streamlit via les variables d'environnement
os.environ['STREAMLIT_SERVER_PORT'] = port
os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'

# Importer et lancer Streamlit
from streamlit.web import cli as stcli

if __name__ == '__main__':
    sys.argv = ['streamlit', 'run', 'upload_video_mixer.py']
    sys.exit(stcli.main())
