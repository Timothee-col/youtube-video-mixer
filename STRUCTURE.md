# 📁 Structure du Projet - YouTube Video Mixer

## 🎯 Vue d'ensemble
YouTube Video Mixer Pro est une application Streamlit qui transforme des vidéos YouTube en contenu vertical optimisé pour TikTok/Reels avec reconnaissance faciale intelligente.

## 📂 Organisation des fichiers

### 🚀 **Application principale**
- `youtube_mixer.py` - Interface utilisateur Streamlit principale
- `event_loop_fix.py` - Correctif asyncio pour Windows/Streamlit

### 🧠 **Intelligence artificielle & traitement**
- `video_processor.py` - Traitement vidéo et assemblage final
- `video_analyzer.py` - Analyse intelligente des segments vidéo
- `face_detector.py` - Reconnaissance faciale avec face-recognition
- `text_detector.py` - Détection et suppression de texte

### 🛠️ **Utilitaires & configuration**
- `utils.py` - Téléchargement YouTube et fonctions utilitaires
- `constants.py` - Configuration et paramètres
- `ytdlp_safe.py` - Wrapper sécurisé pour yt-dlp

### 🚀 **Déploiement**
- `requirements.txt` - Dépendances Python
- `Procfile` - Configuration Heroku/Railway
- `railway.json` - Configuration spécifique Railway
- `nixpacks.toml` - Configuration Nixpacks

### 📚 **Documentation**
- `README.md` - Documentation utilisateur
- `YOUTUBE_FIX.md` - Guide technique YouTube
- `STRUCTURE.md` - Ce fichier

### ⚙️ **Configuration**
- `.gitignore` - Exclusions Git (venv, médias, etc.)

## 🎨 **Architecture technique**

### 🔄 **Flux de traitement**
1. **Téléchargement** (`utils.py`) → URLs YouTube vers vidéos locales
2. **Analyse** (`video_analyzer.py`) → Détection des meilleurs moments
3. **Traitement** (`video_processor.py`) → Conversion format vertical 9:16
4. **Intelligence** (`face_detector.py`, `text_detector.py`) → IA pour optimisation
5. **Assemblage** → Création vidéo finale TikTok/Reels

### 🧩 **Modules spécialisés**
- **Reconnaissance faciale** : Priorise les segments avec visages cibles
- **Détection de texte** : Évite/supprime les zones de texte
- **Crop intelligent** : Cadrage automatique sur les visages
- **Optimisations Railway** : Gestion mémoire adaptative

## 🌍 **Environnements supportés**

### 🏠 **Local**
- Qualité maximale (1080p, bitrate élevé)
- Plus de clips possibles
- Traitement parallèle optimisé

### 🚂 **Railway**
- Optimisations mémoire (limitations RAM)
- Qualité équilibrée (720p)
- Groupes de clips réduits

## 🗑️ **Fichiers supprimés lors du nettoyage**
- ❌ `venv/` - Environnement virtuel (ne doit jamais être versionné)
- ❌ `async_fix.py` - Doublons de correctifs asyncio
- ❌ `simple_fix.py` - Correctifs redondants

## 📊 **Statistiques du projet**
- **11 fichiers actifs** (après nettoyage)
- **~2000 lignes de code** Python
- **Langages** : Python, Streamlit, OpenCV, MoviePy
- **IA** : face-recognition, dlib, text detection

---
*Dernière mise à jour : 2025-08-08*