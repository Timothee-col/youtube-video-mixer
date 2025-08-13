# Dockerfile pour Railway - Version Python
FROM python:3.11-slim

# Installer ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copier et installer les dépendances
COPY requirements-simple.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY . .

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV IS_RAILWAY=true

# Utiliser le script Python qui gère correctement le port
CMD ["python", "run.py"]
