#!/bin/bash

# Script de démarrage pour Railway
echo "🚀 Démarrage de l'application sur Railway"

# Utiliser le port fourni par Railway ou 8501 par défaut
PORT=${PORT:-8501}

echo "📡 Port utilisé: $PORT"
echo "🌐 Adresse: 0.0.0.0"

# Démarrer Streamlit avec le bon port
exec streamlit run upload_video_mixer.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false