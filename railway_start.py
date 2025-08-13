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
    print(f"🌐 Variables d'environnement PORT: {port}")
    
    # IMPORTANT: Supprimer les variables Streamlit conflictuelles
    env = os.environ.copy()
    # Supprimer toutes les variables STREAMLIT_* qui pourraient causer des conflits
    for key in list(env.keys()):
        if key.startswith('STREAMLIT_'):
            print(f"🗑️ Suppression variable conflictuelle: {key}={env[key]}")
            del env[key]
    
    # Ajouter seulement les variables nécessaires
    env['STREAMLIT_SERVER_HEADLESS'] = 'true'
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    # Commande Streamlit avec le port correct
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'upload_video_mixer.py',
        '--server.port', str(port),
        '--server.address', '0.0.0.0',
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false'
    ]
    
    print(f"📡 Commande: {' '.join(cmd)}")
    print(f"🔧 Port utilisé: {port}")
    
    # Lancer Streamlit avec l'environnement nettoyé
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()