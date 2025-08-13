#!/bin/bash
# Script pour choisir la configuration Railway

echo "Configuration Railway"
echo "===================="
echo "1. Version simple (sans reconnaissance faciale) - Déploiement rapide"
echo "2. Version complète (avec reconnaissance faciale) - Plus long"
echo "3. Version conda (plus fiable pour dlib)"
echo ""
read -p "Choisissez une option (1-3): " choice

case $choice in
    1)
        echo "✅ Configuration simple sélectionnée"
        cp Dockerfile.simple Dockerfile
        cp requirements-simple.txt requirements.txt
        echo "NO_FACE_RECOGNITION=true" > .env
        ;;
    2)
        echo "✅ Configuration complète sélectionnée"
        # Le Dockerfile principal est déjà correct
        cp requirements-docker.txt requirements.txt
        ;;
    3)
        echo "✅ Configuration conda sélectionnée"
        cp Dockerfile.conda Dockerfile
        cp requirements-conda.txt requirements.txt
        ;;
    *)
        echo "❌ Option invalide"
        exit 1
        ;;
esac

echo ""
echo "Configuration terminée! Maintenant:"
echo "1. git add ."
echo "2. git commit -m 'Configuration Railway'"
echo "3. git push"
