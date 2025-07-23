"""
Fonctions utilitaires pour YouTube Video Mixer
"""
import os
import tempfile
import shutil
import yt_dlp
import streamlit as st
from typing import List, Dict, Optional, Tuple
from constants import YOUTUBE_DL_OPTIONS, SUPPORTED_EXTENSIONS

def create_temp_directory(base_path: Optional[str] = None) -> str:
    """
    Crée un répertoire temporaire pour la session
    
    Args:
        base_path: Chemin de base (optionnel)
    
    Returns:
        str: Chemin du répertoire temporaire créé
    """
    if base_path:
        temp_dir = tempfile.mkdtemp(dir=base_path)
    else:
        temp_dir = tempfile.mkdtemp()
    
    return temp_dir

def cleanup_temp_files(temp_dir: str) -> bool:
    """
    Nettoie les fichiers temporaires
    
    Args:
        temp_dir: Chemin du répertoire temporaire
    
    Returns:
        bool: True si le nettoyage a réussi
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            return True
    except Exception as e:
        st.error(f"Erreur lors du nettoyage: {str(e)}")
    return False

def download_youtube_videos(urls: List[str], output_dir: str, quality_mode: str = 'high', show_formats: bool = False) -> List[Dict]:
    """
    Télécharge des vidéos YouTube avec contrôle de qualité
    
    Args:
        urls: Liste des URLs YouTube
        output_dir: Répertoire de sortie
        quality_mode: Mode de qualité ('ultra', 'high', 'standard', 'fast')
        show_formats: Afficher les formats disponibles
    
    Returns:
        List[Dict]: Liste des vidéos téléchargées avec leurs métadonnées
    """
    downloaded_files = []
    
    # Configuration selon le mode de qualité
    quality_configs = {
        'ultra': {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'format_sort': ['res', 'vbr', 'tbr'],
            'merge_output_format': 'mp4',
            'postprocessor_args': ['-c:v', 'libx264', '-preset', 'veryslow', '-crf', '15'],
            'prefer_free_formats': False,
            'no_check_certificate': True
        },
        'high': {
            'format': 'bestvideo[height=1080][vbr>2000]/bestvideo[height=1080]/bestvideo[height<=1080]+bestaudio/best',
            'format_sort': ['res:1080', 'vbr', 'tbr'],
            'merge_output_format': 'mp4',
            'postprocessor_args': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18']
        },
        'standard': {
            'format': 'best[height<=1080]',
            'merge_output_format': 'mp4'
        },
        'fast': {
            'format': 'worst[height>=720]',
            'merge_output_format': 'mp4'
        }
    }
    
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'prefer_free_formats': False,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s')
    }
    
    # Fusionner avec la configuration de qualité
    ydl_opts = {**base_opts, **quality_configs.get(quality_mode, quality_configs['high'])}
    
    for idx, url in enumerate(urls):
        try:
            # D'abord, afficher les formats disponibles si demandé
            if show_formats:
                with st.expander(f"📊 Formats disponibles pour vidéo {idx+1}", expanded=False):
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        formats = info.get('formats', [])
                        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
                        video_formats.sort(key=lambda x: (x.get('height', 0), x.get('vbr', 0) or 0), reverse=True)
                        
                        st.write(f"🎬 **Titre:** {info.get('title', 'N/A')}")
                        st.write(f"⏱️ **Durée:** {format_duration(info.get('duration', 0))}")
                        st.write("\nTop 10 formats disponibles:")
                        for i, f in enumerate(video_formats[:10], 1):
                            quality_emoji = "🎯" if f.get('height', 0) >= 1080 else "📹" if f.get('height', 0) >= 720 else "📱"
                            st.write(f"{i}. {quality_emoji} **{f.get('format_id')}**: {f.get('width')}x{f.get('height')} - "
                                    f"{f.get('vcodec')} - {f.get('vbr', 'N/A') if f.get('vbr') else 'N/A'} kbps - "
                                    f"{(f.get('filesize_approx', 0) or 0)/1024/1024:.1f} MB")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Messages de qualité personnalisés
                quality_messages = {
                    'ultra': '🚀 Téléchargement en qualité ULTRA maximale...',
                    'high': '🎯 Téléchargement en haute qualité...',
                    'standard': '📹 Téléchargement en qualité standard...',
                    'fast': '⚡ Téléchargement rapide...'
                }
                st.info(quality_messages.get(quality_mode, 'Téléchargement...'))
                
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Gérer différentes extensions
                actual_filename = None
                for ext in SUPPORTED_EXTENSIONS['video']:
                    test_filename = filename.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(test_filename):
                        actual_filename = test_filename
                        break
                
                if actual_filename:
                    # Obtenir les infos détaillées du format téléchargé
                    format_info = info.get('format_note', 'N/A')
                    resolution = f"{info.get('width', 'N/A')}x{info.get('height', 'N/A')}"
                    bitrate = info.get('vbr', info.get('tbr', 'N/A'))
                    codec = info.get('vcodec', 'N/A')
                    file_size_mb = os.path.getsize(actual_filename) / 1024 / 1024
                    fps = info.get('fps', 'N/A')
                    
                    downloaded_files.append({
                        'path': actual_filename,
                        'title': info['title'],
                        'duration': info.get('duration', 0),
                        'url': url,
                        'index': idx,
                        'resolution': resolution,
                        'bitrate': bitrate,
                        'codec': codec,
                        'file_size_mb': file_size_mb,
                        'fps': fps
                    })
                    
                    # Affichage amélioré des statistiques
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.success(f"✅ {info['title'][:40]}...")
                    with col2:
                        quality_badge = "🏆" if int(info.get('height', 0)) >= 1080 else "🥈" if int(info.get('height', 0)) >= 720 else "🥉"
                        st.metric("Résolution", resolution, quality_badge)
                    with col3:
                        st.metric("Taille", f"{file_size_mb:.1f} MB", f"{bitrate} kbps")
                    
                    # Informations détaillées dans un expander
                    with st.expander(f"🔍 Détails techniques - Vidéo {idx+1}", expanded=False):
                        st.write(f"**Codec vidéo:** {codec}")
                        st.write(f"**FPS:** {fps}")
                        st.write(f"**Format ID:** {info.get('format_id', 'N/A')}")
                        st.write(f"**Audio codec:** {info.get('acodec', 'N/A')}")
                        st.write(f"**Durée:** {format_duration(info.get('duration', 0))}")
                        
                        # Score de qualité
                        quality_score = 0
                        if int(info.get('height', 0)) >= 1080: quality_score += 3
                        elif int(info.get('height', 0)) >= 720: quality_score += 2
                        else: quality_score += 1
                        
                        if bitrate != 'N/A' and int(bitrate) > 2000: quality_score += 2
                        elif bitrate != 'N/A' and int(bitrate) > 1000: quality_score += 1
                        
                        st.progress(quality_score / 5)
                        st.write(f"**Score de qualité:** {'⭐' * quality_score}/5")
                else:
                    st.error(f"❌ Fichier non trouvé après téléchargement: {info['title']}")
                    
        except Exception as e:
            st.error(f"❌ Erreur téléchargement {url}: {str(e)}")
    
    return downloaded_files

def save_uploaded_file(uploaded_file, temp_dir: str, filename: Optional[str] = None) -> Optional[str]:
    """
    Sauvegarde un fichier uploadé dans le répertoire temporaire
    
    Args:
        uploaded_file: Fichier uploadé via Streamlit
        temp_dir: Répertoire temporaire
        filename: Nom du fichier (optionnel)
    
    Returns:
        str: Chemin du fichier sauvegardé ou None si erreur
    """
    try:
        if filename is None:
            filename = uploaded_file.name
        
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        
        return file_path
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du fichier: {str(e)}")
        return None

def get_video_info(video_path: str) -> Dict:
    """
    Obtient les informations d'une vidéo
    
    Args:
        video_path: Chemin de la vidéo
    
    Returns:
        Dict: Informations de la vidéo (durée, dimensions, fps, etc.)
    """
    import cv2
    
    cap = cv2.VideoCapture(video_path)
    
    info = {
        'duration': 0,
        'fps': 0,
        'width': 0,
        'height': 0,
        'frame_count': 0
    }
    
    if cap.isOpened():
        info['fps'] = int(cap.get(cv2.CAP_PROP_FPS))
        info['frame_count'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if info['fps'] > 0:
            info['duration'] = info['frame_count'] / info['fps']
    
    cap.release()
    return info

def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible
    
    Args:
        seconds: Durée en secondes
    
    Returns:
        str: Durée formatée (ex: "1:23")
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"

def validate_video_file(file_path: str) -> bool:
    """
    Valide qu'un fichier vidéo est lisible
    
    Args:
        file_path: Chemin du fichier
    
    Returns:
        bool: True si le fichier est valide
    """
    try:
        info = get_video_info(file_path)
        return info['duration'] > 0 and info['fps'] > 0
    except:
        return False

def ensure_directory_exists(directory: str) -> None:
    """
    S'assure qu'un répertoire existe, le crée si nécessaire
    
    Args:
        directory: Chemin du répertoire
    """
    os.makedirs(directory, exist_ok=True)

def get_unique_filename(directory: str, base_name: str, extension: str) -> str:
    """
    Génère un nom de fichier unique dans un répertoire
    
    Args:
        directory: Répertoire cible
        base_name: Nom de base du fichier
        extension: Extension du fichier
    
    Returns:
        str: Nom de fichier unique
    """
    counter = 1
    filename = f"{base_name}.{extension}"
    
    while os.path.exists(os.path.join(directory, filename)):
        filename = f"{base_name}_{counter}.{extension}"
        counter += 1
    
    return filename

def estimate_processing_time(num_videos: int, total_duration: float, analysis_mode: str) -> float:
    """
    Estime le temps de traitement en fonction des paramètres
    
    Args:
        num_videos: Nombre de vidéos
        total_duration: Durée totale en secondes
        analysis_mode: Mode d'analyse choisi
    
    Returns:
        float: Temps estimé en secondes
    """
    # Temps de base par vidéo
    base_time_per_video = 10
    
    # Facteur selon le mode d'analyse
    mode_factors = {
        '⚡ Rapide (1-2 min)': 0.5,
        '🎯 Précis (3-5 min)': 1.0,
        '🐌 Très précis (5-10 min)': 2.0
    }
    
    mode_factor = mode_factors.get(analysis_mode, 1.0)
    
    # Temps estimé = base + (durée * facteur de complexité)
    estimated_time = (base_time_per_video * num_videos) + (total_duration * 0.1 * mode_factor)
    
    return estimated_time

def display_progress(current: int, total: int, message: str = "") -> None:
    """
    Affiche une barre de progression
    
    Args:
        current: Valeur actuelle
        total: Valeur totale
        message: Message à afficher
    """
    if total > 0:
        progress = current / total
        st.progress(progress)
        if message:
            st.text(f"{message} ({current}/{total})")