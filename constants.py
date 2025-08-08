"""
Constantes et configurations pour YouTube Video Mixer
"""
import os

# Détection de l'environnement Railway
IS_RAILWAY = bool(os.environ.get('RAILWAY_ENVIRONMENT'))

# Formats vidéo (optimisés pour Railway si nécessaire)
if IS_RAILWAY:
    VIDEO_FORMAT = {
        'width': 720,  # Réduit pour Railway
        'height': 1280,  # Format 720p vertical
        'ratio': 9/16,
        'fps': 24,  # FPS réduit
        'bitrate': '2000k'  # Bitrate réduit
    }
else:
    VIDEO_FORMAT = {
        'width': 1080,
        'height': 1920,
        'ratio': 9/16,
        'fps': 30,
        'bitrate': '8000k'
    }

# Paramètres par défaut
DEFAULT_SETTINGS = {
    'output_duration': 60,
    'max_clips_per_video': 3,
    'min_clip_duration': 3,
    'max_clip_duration': 8,
    'exclude_last_seconds': 5,
    'shuffle_clips': True,
    'smart_shuffle': True,
    'face_detection_only': False,
    'smart_crop': True,
    'avoid_text': False
}

# Modes d'analyse
ANALYSIS_MODES = {
    '⚡ Rapide (1-2 min)': {
        'segment_duration': 3,
        'frames_per_segment': 1,
        'max_segments': 30,  # Augmenté de 15 à 30
        'face_model': 'hog',
        'upsample': 0
    },
    '🎯 Précis (3-5 min)': {
        'segment_duration': 1.5,
        'frames_per_segment': 2,
        'max_segments': 60,  # Augmenté de 30 à 60
        'face_model': 'hog',
        'upsample': 1
    },
    '🐌 Très précis (5-10 min)': {
        'segment_duration': 1,
        'frames_per_segment': 3,
        'max_segments': 100,  # Augmenté de 50 à 100
        'face_model': 'hog',
        'upsample': 1
    }
}

# Paramètres de détection
DETECTION_PARAMS = {
    'face_similarity_threshold': 0.4,  # Réduit de 0.6 à 0.4 pour être plus strict
    'text_detection_threshold': 0.5,
    'subtitle_zone_ratio': 0.7,  # Zone du bas pour les sous-titres
    'text_penalty_high': 0.1,     # Pénalité si beaucoup de texte
    'text_penalty_medium': 0.5    # Pénalité si texte modéré
}

# Paramètres de scoring
SCORING_WEIGHTS = {
    'visual_interest': 0.3,
    'face_detection': 0.4,
    'motion': 0.3,
    'face_boost': 2.0  # Multiplicateur si visage cible détecté
}

# URL du modèle EAST pour la détection de texte
EAST_MODEL_URL = "https://github.com/oyyd/frozen_east_text_detection.pb/raw/master/frozen_east_text_detection.pb"

# Messages UI
UI_MESSAGES = {
    'app_title': "YouTube Video Mixer Pro 🎬 - TikTok/Reels Edition",
    'app_subtitle': "Crée des vidéos verticales avec reconnaissance faciale pour les réseaux sociaux!",
    'face_loaded': "✅ Visage de référence chargé! Les clips avec cette personne seront priorisés.",
    'face_not_detected': "⚠️ Aucun visage détecté dans l'image. Vérifiez que le visage est bien visible.",
    'text_model_loaded': "✅ Modèle de détection de texte chargé!",
    'video_created': "✅ Vidéo TikTok/Reels créée avec succès!",
    'temp_cleaned': "Fichiers temporaires supprimés!"
}

# Extensions de fichiers supportées
SUPPORTED_EXTENSIONS = {
    'video': ['mp4', 'mov', 'avi', 'webm', 'mkv'],
    'audio': ['mp3', 'wav', 'm4a', 'aac', 'ogg'],
    'image': ['jpg', 'jpeg', 'png']
}

# Paramètres YouTube-DL pour haute qualité
YOUTUBE_DL_OPTIONS = {
    'format': 'bestvideo[height=1080][vbr>2000]/bestvideo[height=1080]/bestvideo[height<=1080]+bestaudio/best',
    'format_sort': ['res:1080', 'vbr', 'tbr'],  # Prioriser résolution puis bitrate
    'quiet': True,
    'no_warnings': True,
    'merge_output_format': 'mp4',
    'prefer_free_formats': False,  # Préférer AVC/H264
}

# Paramètres OpenCV DNN pour EAST
EAST_DNN_PARAMS = {
    'blob_size': (320, 320),
    'mean_values': (123.68, 116.78, 103.94),
    'swap_rb': True,
    'crop': False
}

# Paramètres d'inpainting
INPAINT_PARAMS = {
    'radius': 3,
    'padding': 5
}