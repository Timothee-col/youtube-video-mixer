"""
Fonctions utilitaires pour YouTube Video Mixer - Version corrigée
"""
import os
import tempfile
import shutil
import streamlit as st
import time
from typing import List, Dict, Optional, Tuple
from constants import YOUTUBE_DL_OPTIONS, SUPPORTED_EXTENSIONS, IS_RAILWAY

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

def get_best_available_format(url: str, quality_mode: str) -> str:
    """
    Analyse les formats disponibles pour une vidéo et retourne un sélecteur intelligent
    
    Args:
        url: URL de la vidéo YouTube
        quality_mode: Mode de qualité demandé
        
    Returns:
        str: Format selector string intelligent basé sur les caractéristiques
    """
    # Configuration style "YouTube to MP4" - priorité aux clients mobiles
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'force_generic_extractor': False,
        # Stratégie mobile-first comme les sites de téléchargement
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android'],  # iOS en premier !
                'skip': ['hls', 'dash'],  # Formats directs seulement
                'player_skip': ['webpage', 'configs'],  # Skip les checks inutiles
            }
        },
        # Headers mobiles pour éviter la détection
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
            
            # Analyser ce qui est réellement disponible
            has_1080p_premium = any(f.get('height') == 1080 and (f.get('vbr', 0) or 0) > 3000 for f in video_formats)
            has_1080p_standard = any(f.get('height') == 1080 and (f.get('vbr', 0) or 0) > 500 for f in video_formats)
            has_720p_good = any(f.get('height') == 720 and (f.get('vbr', 0) or 0) > 1000 for f in video_formats)
            has_720p = any(f.get('height') == 720 for f in video_formats)
            has_480p = any(f.get('height') == 480 for f in video_formats)
            
            # STRATÉGIE YOUTUBE-TO-MP4: Privilégier les formats directs MP4
            # Chercher d'abord les formats MP4 complets (video+audio)
            mp4_formats_1080p = [f for f in video_formats if f.get('ext') == 'mp4' and f.get('height') == 1080 and f.get('acodec') != 'none']
            mp4_formats_720p = [f for f in video_formats if f.get('ext') == 'mp4' and f.get('height') == 720 and f.get('acodec') != 'none']
            
            if quality_mode == 'ultra':
                selectors = []
                # Priorité aux MP4 directs (comme les sites de téléchargement)
                if mp4_formats_1080p:
                    best_mp4 = max(mp4_formats_1080p, key=lambda x: x.get('vbr', 0) or 0)
                    selectors.append(str(best_mp4.get('format_id')))
                if mp4_formats_720p:
                    best_720_mp4 = max(mp4_formats_720p, key=lambda x: x.get('vbr', 0) or 0) 
                    selectors.append(str(best_720_mp4.get('format_id')))
                # Puis les formats séparés si nécessaire
                if has_1080p_premium:
                    selectors.append('bestvideo[height=1080][vbr>3000]+bestaudio/best')
                if has_1080p_standard:
                    selectors.append('bestvideo[height=1080]+bestaudio/best')
                # Fallback génériques
                selectors.append('best[height>=720][ext=mp4]')
                selectors.append('best[height>=720]')
                selectors.append('best')
                return '/'.join(selectors)
                    
            elif quality_mode == 'high':
                # High: Équilibré entre qualité et compatibilité
                selectors = []
                # Priorité aux MP4 directs (comme les sites de téléchargement)
                if mp4_formats_1080p:
                    selectors.append(str(mp4_formats_1080p[0].get('format_id')))
                if mp4_formats_720p:
                    selectors.append(str(mp4_formats_720p[0].get('format_id')))
                # Puis les formats séparés si nécessaire
                if has_1080p_standard:
                    selectors.append('bestvideo[height=1080]+bestaudio')
                if has_720p:
                    selectors.append('bestvideo[height=720]+bestaudio')
                selectors.append('best[height>=720][ext=mp4]')
                selectors.append('best[height>=720]') 
                selectors.append('best')
                return '/'.join(selectors)
                    
            elif quality_mode == 'standard':
                # Standard: Compatible et fiable
                selectors = []
                # Chercher les MP4 directs en 720p et 480p
                mp4_formats_480p = [f for f in video_formats if f.get('ext') == 'mp4' and f.get('height') == 480 and f.get('acodec') != 'none']
                if mp4_formats_720p:
                    selectors.append(str(mp4_formats_720p[0].get('format_id')))
                if mp4_formats_480p:
                    selectors.append(str(mp4_formats_480p[0].get('format_id')))
                # Puis les formats séparés
                if has_720p:
                    selectors.append('bestvideo[height=720]+bestaudio')
                if has_480p:
                    selectors.append('bestvideo[height=480]+bestaudio')
                selectors.append('best[height>=480][ext=mp4]')
                selectors.append('best[height>=480]')
                selectors.append('best')
                return '/'.join(selectors)
                
            else:  # fast
                # Fast: Prendre ce qui marche, privilégier MP4
                return 'best[ext=mp4]/best/bestvideo+bestaudio'
            
    except Exception as e:
        st.warning(f"⚠️ Analyse des formats échouée: {str(e)[:100]}...")
        # Fallback encore plus robuste
        if quality_mode == 'ultra':
            return 'bestvideo[height>=1080]+bestaudio/bestvideo[height>=720]+bestaudio/best[height>=720]/best[height>=480]/best'
        elif quality_mode == 'high':
            return 'bestvideo[height>=720]+bestaudio/best[height>=720]/best[height>=480]/best'
        elif quality_mode == 'standard':
            return 'best[height>=480]/best[height>=360]/best'
        else:
            return 'best'

def download_youtube_videos(urls: List[str], output_dir: str, quality_mode: str = 'high', show_formats: bool = False) -> List[Dict]:
    """
    Télécharge des vidéos YouTube avec détection intelligente des formats disponibles
    
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
    
    # NOUVEAU 2025: Détection intelligente des formats pour chaque URL
    st.info(f"🔍 Mode {quality_mode}: Analyse intelligente des formats disponibles...")
    
    # STRATÉGIE "YOUTUBE TO MP4" - Options optimisées comme les sites de téléchargement
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    base_opts = {
        'quiet': False,
        'no_warnings': False,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'windowsfilenames': True,
        # Post-processing minimal pour vitesse
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'keepvideo': False,
        'overwrites': True,
        'nocheckcertificate': True,
        # Options de téléchargement optimisées
        'concurrent_fragment_downloads': 4,  # Plus de parallélisme
        'http_chunk_size': 10485760,
        'retries': 5,  # Plus de tentatives
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'ignoreerrors': False,
        'fixup': 'detect_or_warn',
        'prefer_ffmpeg': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'extractor_retries': 5,
        # Headers mobiles
        'http_headers': mobile_headers,
        # Pas de délais (comme les sites rapides)
        'sleep_interval': 0,
        'max_sleep_interval': 0,
        'sleep_interval_requests': 0,
        # STRATÉGIE MOBILE-FIRST
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android', 'tv_embedded'],  # iOS prioritaire
                'skip': ['hls', 'dash'] if quality_mode != 'ultra' else ['dash'],  # Direct MP4
                'player_skip': ['webpage', 'js'],  # Skip inutile
                'formats': 'incomplete',  # Accepter formats incomplets
            }
        },
        # Bypass geo et age
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'age_limit': None,
    }
    
    # Configuration de base pour tous les téléchargements
    base_download_opts = {
        'merge_output_format': 'mp4',
        # Le format sera défini dynamiquement par URL
    }
    
    # DEBUG: Stratégie YouTube to MP4 2025
    if IS_RAILWAY:
        st.warning("🚂 Railway détecté - Mode bypass activé")
        # Simuler une requête depuis un embedder populaire
        base_opts['http_headers']['Referer'] = 'https://www.y2mate.com/'
        base_opts['http_headers']['Origin'] = 'https://www.y2mate.com'
        # Forcer le client embedder
        base_opts['extractor_args']['youtube']['player_client'].insert(0, 'web_embedded')
    
    st.success("✅ STRATÉGIE YOUTUBE-TO-MP4 2025 - Bypass comme les pros")
    st.info(f"📱 Clients: {base_opts['extractor_args']['youtube'].get('player_client', 'ERREUR')}")
    st.info(f"🌍 Mode: {'Railway Bypass' if IS_RAILWAY else 'Local Direct'}")
    st.info(f"🎯 Headers: Mobile iOS 17")
    
    # Mode avec détection intelligente
    if quality_mode == 'ultra':
        st.success(f"🚀 Mode ULTRA: Recherche formats premium (>3000 kbps)")
    elif quality_mode == 'high':
        st.info(f"📹 Mode HIGH: Recherche 1080p standard puis 720p")
    else:
        st.info(f"📺 Mode {quality_mode}: Optimisé pour la compatibilité")
    
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
            
            # ÉTAPE 1: Analyser les formats disponibles pour cette vidéo spécifique
            optimal_format = None
            try:
                with st.spinner(f"🔍 Analyse des formats pour vidéo {idx+1}..."):
                    optimal_format = get_best_available_format(url, quality_mode)
                    st.info(f"🎯 Format optimal détecté: {optimal_format[:50]}...")
            except Exception as e:
                st.warning(f"⚠️ Analyse échouée, utilisation du format par défaut")
                # Format par défaut selon le mode
                if quality_mode == 'ultra':
                    optimal_format = 'best[height>=720]/best[height>=480]/best'
                elif quality_mode == 'high':
                    optimal_format = 'best[height>=720]/best[height>=480]/best'
                else:
                    optimal_format = 'best'
            
            # ÉTAPE 2: Télécharger avec le format optimal
            download_success = False
            attempts = 0
            max_attempts = 3
            
            while not download_success and attempts < max_attempts:
                attempts += 1
                
                try:
                    # Créer les options avec le format optimal détecté
                    ydl_opts = {**base_opts, **base_download_opts, 'format': optimal_format}
                    
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
                        
                        # Télécharger avec DÉTECTION INTELLIGENTE 2025
                        quality_messages = {
                            'ultra': f'🚀 INTELLIGENT 2025: Téléchargement format premium...',
                            'high': f'🎯 INTELLIGENT 2025: Téléchargement format optimal...',
                            'standard': f'📹 INTELLIGENT 2025: Téléchargement adaptatif...',
                            'fast': f'⚡ INTELLIGENT 2025: Téléchargement rapide...'
                        }
                        
                        with st.spinner(quality_messages.get(quality_mode, f'🤖 Format {optimal_format[:20]}...')):
                            info = ydl.extract_info(url, download=True)
                            
                            # Vérification qualité téléchargée
                            if info:
                                format_id = info.get('format_id', 'inconnu')
                                height = info.get('height', 0)
                                vbr = info.get('vbr', 0) or 0
                                
                                if format_id == '18':
                                    st.error(f"🚨 Format 18 malgré détection intelligente! Vidéo très restreinte!")
                                    st.warning("YouTube bloque complètement cette vidéo")
                                else:
                                    st.success(f"✅ DÉTECTION RÉUSSIE: Format {format_id} ({height}p, {vbr} kbps)")
                                    
                                # Évaluation de la qualité obtenue
                                if height >= 1080 and vbr > 3000:
                                    st.success(f"🏆 PREMIUM HD OBTENU! {height}p à {vbr} kbps")
                                elif height >= 1080:
                                    st.success(f"🥇 FULL HD OBTENU! {height}p à {vbr} kbps") 
                                elif height >= 720:
                                    st.info(f"🥈 HD OBTENU! {height}p à {vbr} kbps")
                                elif height >= 480:
                                    st.warning(f"🥉 SD obtenu: {height}p à {vbr} kbps")
                                else:
                                    st.error(f"❌ Qualité faible: {height}p à {vbr} kbps")
                            
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
                        # Simplifier les options et le format
                        fallback_opts = ydl_opts.copy()
                        fallback_opts['format'] = 'best[ext=mp4]/best'
                        fallback_opts.pop('concurrent_fragment_downloads', None)
                        ydl_opts = fallback_opts
                        
                    elif "Requested format is not available" in error_msg:
                        st.warning("⚠️ Format demandé non disponible, simplification...")
                        # Utiliser un format plus simple
                        simple_opts = ydl_opts.copy()
                        simple_opts['format'] = 'best'
                        ydl_opts = simple_opts
                        
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
