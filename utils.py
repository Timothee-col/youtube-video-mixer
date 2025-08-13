"""
Fonctions utilitaires pour Upload Video Mixer - Version Upload Only
"""
import os
import tempfile
import shutil
import streamlit as st
import time
from typing import List, Dict, Optional, Tuple
from constants import SUPPORTED_EXTENSIONS

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

def save_uploaded_file(uploaded_file, temp_dir: str, filename: str) -> Optional[str]:
    """
    Sauvegarde un fichier uploadé dans le répertoire temporaire
    
    Args:
        uploaded_file: Fichier Streamlit uploadé
        temp_dir: Répertoire temporaire
        filename: Nom du fichier (sera sécurisé)
    
    Returns:
        str: Chemin du fichier sauvegardé ou None si erreur
    """
    try:
        # Sécuriser le nom de fichier
        safe_name = safe_filename(filename)
        file_path = os.path.join(temp_dir, safe_name)
        
        # Sauvegarder le fichier
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du fichier: {str(e)}")
        return None

def validate_and_convert_video(file_path: str, temp_dir: str) -> Optional[str]:
    """
    Valide et convertit une vidéo pour s'assurer qu'elle est compatible avec MoviePy
    
    Args:
        file_path: Chemin du fichier vidéo
        temp_dir: Répertoire temporaire
    
    Returns:
        str: Chemin du fichier converti ou original si OK
    """
    try:
        # Test initial avec MoviePy
        test_clip = None
        try:
            from moviepy.editor import VideoFileClip
            test_clip = VideoFileClip(file_path)
            
            # Test d'accès aux frames
            test_frame = test_clip.get_frame(0.1)
            if test_frame is not None:
                test_clip.close()
                st.success(f"✅ Vidéo compatible directement")
                return file_path
            else:
                st.warning("⚠️ Vidéo retourne frames None, conversion nécessaire")
                test_clip.close()
                
        except Exception as e:
            st.warning(f"⚠️ Erreur MoviePy: {str(e)}, conversion nécessaire")
            if test_clip:
                test_clip.close()
        
        # Conversion nécessaire
        st.info("🔄 Conversion de la vidéo en format compatible...")
        
        # Utiliser ffmpeg pour convertir en H.264 MP4 compatible
        converted_path = os.path.join(temp_dir, f"converted_{os.path.basename(file_path)}")
        
        import subprocess
        cmd = [
            'ffmpeg', '-i', file_path,
            '-c:v', 'libx264',  # Force H.264
            '-c:a', 'aac',      # Force AAC audio
            '-preset', 'fast',   # Conversion rapide
            '-crf', '23',       # Qualité raisonnable
            '-movflags', '+faststart',  # Optimisation web
            '-y',               # Overwrite
            converted_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(converted_path):
            # Test du fichier converti
            try:
                test_clip = VideoFileClip(converted_path)
                test_frame = test_clip.get_frame(0.1)
                test_clip.close()
                
                if test_frame is not None:
                    st.success("✅ Conversion réussie, vidéo compatible")
                    return converted_path
                else:
                    st.error("❌ Vidéo convertie toujours incompatible")
                    return None
            except Exception as e:
                st.error(f"❌ Vidéo convertie non fonctionnelle: {str(e)}")
                return None
        else:
            st.error(f"❌ Échec de conversion ffmpeg: {result.stderr}")
            return None
            
    except Exception as e:
        st.error(f"❌ Erreur validation vidéo: {str(e)}")
        return None

def process_uploaded_videos(uploaded_files, temp_dir: str) -> List[Dict]:
    """
    Traite les fichiers vidéo uploadés avec validation et conversion si nécessaire
    """
    processed_files = []
    
    if not uploaded_files:
        st.warning("⚠️ Aucun fichier uploadé")
        return processed_files
    
    st.info(f"📁 Traitement de {len(uploaded_files)} fichier(s) uploadé(s)...")
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            # Vérifier l'extension
            filename = uploaded_file.name
            _, ext = os.path.splitext(filename.lower())
            
            if ext not in SUPPORTED_EXTENSIONS:
                st.error(f"❌ Format non supporté: {filename} ({ext})")
                st.info(f"Formats supportés: {', '.join(SUPPORTED_EXTENSIONS)}")
                continue
            
            # Sauvegarder le fichier
            file_path = save_uploaded_file(uploaded_file, temp_dir, filename)
            
            if not file_path or not os.path.exists(file_path):
                st.error(f"❌ Impossible de sauvegarder: {filename}")
                continue
            
            # VALIDATION ET CONVERSION si nécessaire
            st.info(f"🔍 Validation de {filename}...")
            validated_path = validate_and_convert_video(file_path, temp_dir)
            
            if not validated_path:
                st.error(f"❌ Impossible de traiter {filename} - format incompatible")
                continue
            
            # Obtenir les informations du fichier validé
            file_size_mb = os.path.getsize(validated_path) / 1024 / 1024
            
            # Extraire les métadonnées avec le fichier validé
            try:
                from moviepy.editor import VideoFileClip
                with VideoFileClip(validated_path) as clip:
                    duration = clip.duration
                    fps = clip.fps
                    width, height = clip.size
            except Exception as e:
                st.warning(f"⚠️ Erreur métadonnées: {str(e)}")
                duration = 0
                fps = 'N/A'
                width, height = 'N/A', 'N/A'
            
            processed_files.append({
                'path': validated_path,  # Utiliser le fichier validé
                'title': os.path.splitext(filename)[0],
                'original_filename': filename,
                'duration': duration,
                'index': idx,
                'resolution': f"{width}x{height}",
                'fps': fps,
                'file_size_mb': file_size_mb,
                'source': 'upload',
                'converted': validated_path != file_path
            })
            
            st.success(f"✅ {filename} traité ({file_size_mb:.1f} MB)")
            
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement de {uploaded_file.name}: {str(e)}")
            continue
    
    if not processed_files:
        st.error("❌ Aucun fichier n'a pu être traité")
    else:
        st.success(f"✅ {len(processed_files)} fichier(s) traité(s) avec succès")
    
    return processed_files

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

def validate_uploaded_file(uploaded_file) -> bool:
    """
    Valide qu'un fichier uploadé est valide
    
    Args:
        uploaded_file: Fichier Streamlit uploadé
    
    Returns:
        bool: True si le fichier est valide
    """
    if not uploaded_file:
        return False
    
    # Vérifier l'extension
    filename = uploaded_file.name
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in SUPPORTED_EXTENSIONS:
        return False
    
    # Vérifier la taille (max 500MB par fichier)
    if uploaded_file.size > 500 * 1024 * 1024:
        st.error(f"❌ Fichier trop volumineux: {filename} ({uploaded_file.size/1024/1024:.1f} MB)")
        st.info("Taille maximale: 500 MB par fichier")
        return False
    
    return True