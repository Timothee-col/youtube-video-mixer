"""
Constantes et configurations pour Upload Video Mixer
"""
import os

# Détection de l'environnement (pour compatibilité)
IS_RAILWAY = False

# Formats vidéo - HAUTE QUALITÉ maintenue
VIDEO_FORMAT = {
    'width': 1080,
    'height': 1920,
    'ratio': 9/16,
    'fps': 30,
    'bitrate': '6000k'
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
        'max_segments': 30,
        'face_model': 'hog',
        'upsample': 0
    },
    '🎯 Précis (3-5 min)': {
        'segment_duration': 1.5,
        'frames_per_segment': 2,
        'max_segments': 60,
        'face_model': 'hog',
        'upsample': 1
    },
    '🐌 Très précis (5-10 min)': {
        'segment_duration': 1,
        'frames_per_segment': 3,
        'max_segments': 100,
        'face_model': 'hog',
        'upsample': 1
    }
}

# Paramètres de détection
DETECTION_PARAMS = {
    'face_similarity_threshold': 0.4,
    'text_detection_threshold': 0.5,
    'subtitle_zone_ratio': 0.7,
    'text_penalty_high': 0.1,
    'text_penalty_medium': 0.5
}

# Paramètres de scoring
SCORING_WEIGHTS = {
    'visual_interest': 0.3,
    'face_detection': 0.4,
    'motion': 0.3,
    'face_boost': 2.0
}

# URL du modèle EAST pour la détection de texte
EAST_MODEL_URL = "https://github.com/oyyd/frozen_east_text_detection.pb/raw/master/frozen_east_text_detection.pb"

# Messages UI
UI_MESSAGES = {
    'app_title': "Upload Video Mixer Pro 🎬 - TikTok/Reels Edition",
    'app_subtitle': "Crée des vidéos verticales avec reconnaissance faciale à partir de tes vidéos uploadées!",
    'face_loaded': "✅ Visage de référence chargé! Les clips avec cette personne seront priorisés.",
    'face_not_detected': "⚠️ Aucun visage détecté dans l'image. Vérifiez que le visage est bien visible.",
    'text_model_loaded': "✅ Modèle de détection de texte chargé!",
    'video_created': "✅ Vidéo TikTok/Reels créée avec succès!",
    'temp_cleaned': "Fichiers temporaires supprimés!"
}

# Extensions de fichiers supportées
SUPPORTED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.webm', '.mkv']

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