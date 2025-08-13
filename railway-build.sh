#!/bin/bash
# Script de build pour Railway

echo "🚂 Railway Build Script"
echo "======================"

# Installer cmake si nécessaire
if ! command -v cmake &> /dev/null; then
    echo "📦 Installation de cmake..."
    apt-get update && apt-get install -y cmake build-essential
fi

# Vérifier si on peut installer face-recognition
echo "🔍 Tentative d'installation de face-recognition..."
if pip install face-recognition==1.3.0; then
    echo "✅ Face-recognition installé avec succès"
else
    echo "⚠️ Face-recognition non disponible, utilisation du mode sans reconnaissance faciale"
    # Utiliser les requirements allégés
    pip install -r requirements-railway.txt
    exit 0
fi

# Installer tous les requirements
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

echo "✅ Build terminé!"
