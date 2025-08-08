"""
Fonctions utilitaires pour YouTube Video Mixer - Version corrigée
"""
import os
import tempfile
import shutil
import streamlit as st
import time
from typing import List, Dict, Optional, Tuple
from constants import YOUTUBE_DL_OPTIONS, SUPPORTED_EXTENSIONS

# Import de yt-dlp
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    yt_dlp = None
    st.error("⚠️ yt-dlp n'est pas installé. Veuillez vérifier requirements.txt")

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
    
    # S'assurer que le répertoire existe et est accessible
    os.makedirs(temp_dir, exist_ok=True)
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

def safe_filename(filename: str) -> str:
    """
    Nettoie le nom de fichier pour éviter les problèmes
    
    Args:
        filename: Nom de fichier original
    
    Returns:
        str: Nom de fichier sécurisé
    """
    # Remplacer les caractères problématiques
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limiter la longueur
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return name + ext

def download_youtube_videos(urls: List[str], output_dir: str, quality_mode: str = 'high', show_formats: bool = False) -> List[Dict]:
    """
    Télécharge des vidéos YouTube avec contrôle de qualité et gestion d'erreurs améliorée
    
    Args:
        urls: Liste des URLs YouTube
        output_dir: Répertoire de sortie
        quality_mode: Mode de qualité ('ultra', 'high', 'standard', 'fast')
        show_formats: Afficher les formats disponibles
    
    Returns:
        List[Dict]: Liste des vidéos téléchargées avec leurs métadonnées
    """
    # Vérifier que yt-dlp est disponible
    if not YT_DLP_AVAILABLE or yt_dlp is None:
        st.error("❌ yt-dlp n'est pas disponible. Impossible de télécharger les vidéos.")
        st.info("💡 Vérifiez que yt-dlp est dans requirements.txt")
        return []
    
    downloaded_files = []
    
    # S'assurer que le répertoire de sortie existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Configuration selon le mode de qualité
    quality_configs = {
        'ultra': {
            # CORRECTION 2025: Priorité HD avec fallback progressif
            'format': 'best[height>=1080]/best[height>=720]/best[height>=480]/best',
            'merge_output_format': 'mp4'
        },
        'high': {
            # CORRECTION 2025: Forcer 720p minimum avec fallback intelligent
            'format': 'best[height>=720]/best[height>=480]/best',
            'merge_output_format': 'mp4'
        },
        'standard': {
            # 480p minimum acceptable
            'format': 'best[height>=480]/best',
            'merge_output_format': 'mp4'
        },
        'fast': {
            # Dernier recours: n'importe quel format
            'format': 'best/worst',
            'merge_output_format': 'mp4'
        }
    }
    
    # Options de base avec corrections ANTI-BOT
    base_opts = {
        'quiet': False,  # Activer les logs pour debug
        'no_warnings': False,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,  # Éviter les caractères problématiques
        'windowsfilenames': True,   # Compatible avec tous les OS
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'keepvideo': False,
        'overwrites': True,
        'nocheckcertificate': True,
        'no_color': True,
        'concurrent_fragment_downloads': 1,
        'http_chunk_size': 10485760,  # 10MB chunks
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'ignoreerrors': False,
        'fixup': 'detect_or_warn',
        'prefer_ffmpeg': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'extractor_retries': 3,
        # ===== OPTIONS ANTI-BOT =====
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        'sleep_interval': 1,  # Pause entre les téléchargements
        'max_sleep_interval': 3,
        'sleep_interval_requests': 0.5,  # Pause entre les requêtes
        # CORRECTION 2025: YOUTUBE PO TOKEN FIX
        'extractor_args': {
            'youtube': {
                'skip': ['dash'],  # Garder HLS pour meilleure qualité
                'player_client': ['android', 'web'],  # Revenir aux clients qui marchaient
                'formats': 'missing_pot'  # IMPORTANT: Activer les formats sans PO token
            }
        },
        # Force le client web si android échoue
        'force_generic_extractor': False,
        # Options pour contourner les restrictions YouTube
        'geo_bypass': True,
        'geo_bypass_country': 'DE'  # Allemagne au lieu des US
    }
    
    # NOUVEAU CODE 2025 - Fusionner avec la configuration de qualité HD FORCÉE
    selected_quality = quality_configs.get(quality_mode, quality_configs['high'])
    ydl_opts = {**base_opts, **selected_quality}
    
    # DEBUG: Version restaurée qui marchait localement  
    st.success("✅ VERSION LOCALE RESTAURÉE - Clients android/web")
    st.info(f"🔧 Format: {ydl_opts.get('format', 'ERREUR')}")
    st.info(f"🔑 Client: {ydl_opts['extractor_args']['youtube'].get('player_client', 'ERREUR')}")
    
    # Mode avec clients Android/Web restaurés
    if quality_mode == 'ultra':
        st.success(f"🚀 Mode ULTRA avec clients restaurés - HD attendu!")
    else:
        st.info(f"📺 Mode {quality_mode} avec clients Android/Web")
    
    for idx, url in enumerate(urls):
        try:
            # Nettoyer l'URL
            if 'youtube.com' in url or 'youtu.be' in url:
                if 'watch?v=' in url:
                    video_id = url.split('watch?v=')[1].split('&')[0]
                    url = f'https://www.youtube.com/watch?v={video_id}'
                elif 'youtu.be/' in url:
                    video_id = url.split('youtu.be/')[1].split('?')[0]
                    url = f'https://www.youtube.com/watch?v={video_id}'
            
            st.info(f"🎥 Téléchargement vidéo {idx+1}/{len(urls)}: {url}")
            
            # Première tentative avec options normales
            download_success = False
            attempts = 0
            max_attempts = 3
            
            while not download_success and attempts < max_attempts:
                attempts += 1
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        if attempts > 1:
                            st.info(f"⏳ Tentative {attempts}/{max_attempts}...")
                        
                        # Extraire les infos d'abord
                        info = ydl.extract_info(url, download=False)
                        if not info:
                            raise Exception("Impossible d'extraire les informations")
                        
                        # Afficher les formats si demandé
                        if show_formats and attempts == 1:
                            with st.expander(f"📊 Formats disponibles pour vidéo {idx+1}", expanded=False):
                                formats = info.get('formats', [])
                                video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
                                video_formats.sort(key=lambda x: (x.get('height', 0), x.get('vbr', 0) or 0), reverse=True)
                                
                                st.write(f"🎬 **Titre:** {info.get('title', 'N/A')}")
                                st.write(f"⏱️ **Durée:** {format_duration(info.get('duration', 0))}")
                                st.write("\nTop 10 formats disponibles:")
                                for i, f in enumerate(video_formats[:10], 1):
                                    quality_emoji = "🎯" if f.get('height', 0) >= 1080 else "📹" if f.get('height', 0) >= 720 else "📱"
                                    st.write(f"{i}. {quality_emoji} **{f.get('format_id')}**: {f.get('width')}x{f.get('height')} - "
                                            f"{f.get('vcodec')} - {f.get('vbr', 'N/A') if f.get('vbr') else 'N/A'} kbps")
                        
                        # Télécharger avec NOUVEAU CODE 2025
                        quality_messages = {
                            'ultra': '🚀 NOUVEAU 2025: Téléchargement ULTRA HD avec fix PO Token...',
                            'high': '🎯 NOUVEAU 2025: Téléchargement HD avec fix PO Token...',
                            'standard': '📹 NOUVEAU 2025: Téléchargement optimisé...',
                            'fast': '⚡ NOUVEAU 2025: Téléchargement rapide...'
                        }
                        
                        with st.spinner(quality_messages.get(quality_mode, 'Téléchargement NOUVEAU 2025...')):
                            info = ydl.extract_info(url, download=True)
                            
                            # Vérification qualité téléchargée
                            if info:
                                format_id = info.get('format_id', 'inconnu')
                                height = info.get('height', 0)
                                if format_id == '18':
                                    st.error(f"🚨 Format 18 MÊITE avec CLIENT TV! Vidéo VRAIMENT bloquée!")
                                    st.warning("Cause probable: 'Playback on other websites has been disabled'")
                                else:
                                    st.success(f"✅ CLIENT TV RÉUSSIT: Format {format_id} ({height}p)")
                                    
                                if height >= 720:
                                    st.success(f"🏆 CLIENT TV VICTOIRE! Qualité HD ({height}p)!")
                                elif height >= 480:
                                    st.info(f"📺 CLIENT TV: Qualité correcte ({height}p)")
                                else:
                                    st.warning(f"⚠️ Même CLIENT TV donne que ({height}p) - Vidéo très restreinte")
                            
                            download_success = True
                            
                except Exception as e:
                    error_msg = str(e)
                    if "Unable to rename file" in error_msg:
                        st.warning("⚠️ Problème de renommage, nouvelle tentative...")
                        # Attendre un peu avant de réessayer
                        time.sleep(2)
                        
                        # Essayer avec un nom de fichier plus simple
                        simple_opts = ydl_opts.copy()
                        simple_opts['outtmpl'] = os.path.join(output_dir, f'video_{idx+1}.%(ext)s')
                        ydl_opts = simple_opts
                        
                    elif "403" in error_msg or "forbidden" in error_msg.lower():
                        st.warning("⚠️ Erreur 403, essai avec méthode alternative...")
                        # Simplifier les options
                        fallback_opts = ydl_opts.copy()
                        fallback_opts['format'] = 'best[ext=mp4]/best'
                        fallback_opts.pop('concurrent_fragment_downloads', None)
                        ydl_opts = fallback_opts
                        
                    elif attempts >= max_attempts:
                        st.error(f"❌ Échec après {max_attempts} tentatives: {error_msg}")
                        break
                    else:
                        st.warning(f"⚠️ Erreur: {error_msg[:100]}... Nouvelle tentative...")
                        time.sleep(1)
            
            if download_success and info:
                # Trouver le fichier téléchargé
                filename = ydl.prepare_filename(info)
                actual_filename = None
                
                # Chercher le fichier avec différentes extensions
                for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov']:
                    test_filename = filename.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(test_filename):
                        actual_filename = test_filename
                        break
                
                # Si pas trouvé, chercher dans le répertoire
                if not actual_filename:
                    for file in os.listdir(output_dir):
                        if file.startswith('video_') and file.endswith('.mp4'):
                            actual_filename = os.path.join(output_dir, file)
                            if os.path.exists(actual_filename):
                                break
                
                if actual_filename and os.path.exists(actual_filename):
                    # Obtenir les infos du fichier
                    file_size_mb = os.path.getsize(actual_filename) / 1024 / 1024
                    
                    downloaded_files.append({
                        'path': actual_filename,
                        'title': info.get('title', f'Video {idx+1}'),
                        'duration': info.get('duration', 0),
                        'url': url,
                        'index': idx,
                        'resolution': f"{info.get('width', 'N/A')}x{info.get('height', 'N/A')}",
                        'bitrate': info.get('vbr', info.get('tbr', 'N/A')),
                        'codec': info.get('vcodec', 'N/A'),
                        'file_size_mb': file_size_mb,
                        'fps': info.get('fps', 'N/A')
                    })
                    
                    # Afficher le succès avec indicateur de qualité amélioré
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.success(f"✅ Téléchargé: {info.get('title', 'Video')[:40]}...")
                    with col2:
                        height = int(info.get('height', 0))
                        if height >= 1080:
                            quality_badge = "🏆 FULL HD"
                            st.success(f"{quality_badge} {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
                        elif height >= 720:
                            quality_badge = "🥈 HD"
                            st.info(f"{quality_badge} {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
                        elif height >= 480:
                            quality_badge = "🥉 SD"
                            st.warning(f"{quality_badge} {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
                        else:
                            quality_badge = "❌ MAUVAISE"
                            st.error(f"{quality_badge} {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
                    with col3:
                        st.info(f"📦 {file_size_mb:.1f} MB")
                else:
                    st.error(f"❌ Fichier téléchargé introuvable pour vidéo {idx+1}")
                    
        except Exception as e:
            st.error(f"❌ Erreur finale pour vidéo {idx+1}: {str(e)}")
            continue
    
    if not downloaded_files:
        st.error("❌ Aucune vidéo n'a pu être téléchargée")
    else:
        st.success(f"✅ {len(downloaded_files)}/{len(urls)} vidéos téléchargées avec succès!")
    
    return downloaded_files

# Les autres fonctions restent identiques...
def save_uploaded_file(uploaded_file, temp_dir: str, filename: str) -> Optional[str]:
    """Sauvegarde un fichier uploadé"""
    try:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du fichier: {str(e)}")
        return None

def format_duration(seconds) -> str:
    """Formate une durée en secondes"""
    # Convertir en int si c'est une chaîne
    if isinstance(seconds, str):
        # Si c'est déjà formaté, le retourner tel quel
        if any(x in seconds for x in ['secondes', 'minutes', 'heures', 's', 'm', 'h']):
            return seconds
        try:
            seconds = int(seconds)
        except ValueError:
            return seconds
    
    seconds = int(seconds) if seconds else 0
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

def estimate_processing_time(num_videos: int, duration: int, has_face: bool) -> str:
    """Estime le temps de traitement"""
    base_time = num_videos * duration * 0.5
    if has_face:
        base_time *= 1.5
    
    if base_time < 60:
        return f"~{int(base_time)} secondes"
    else:
        return f"~{int(base_time/60)} minutes"
