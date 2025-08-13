# Dockerfile simple pour Railway (sans reconnaissance faciale)
FROM python:3.11-slim

# Installer uniquement ffmpeg pour le traitement vidéo
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les requirements allégés
COPY requirements-simple.txt requirements.txt

# Installer les dépendances
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY . .

# Variables d'environnement
ENV IS_RAILWAY=true
ENV PYTHONUNBUFFERED=1
ENV NO_FACE_RECOGNITION=true

# Copier le script de démarrage Python
COPY railway_start.py /app/railway_start.py
RUN chmod +x /app/railway_start.py

# Utiliser le script Python pour démarrer
CMD ["python3", "/app/railway_start.py"]
