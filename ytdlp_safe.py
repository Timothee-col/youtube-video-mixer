"""
Module d'import sécurisé pour yt-dlp
"""
import sys
import subprocess

def ensure_ytdlp():
    """S'assure que yt-dlp est installé et fonctionnel"""
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        print("⚠️ yt-dlp non trouvé, tentative d'installation...")
        try:
            # Essayer d'installer yt-dlp
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
            import yt_dlp
            return yt_dlp
        except Exception as e:
            print(f"❌ Impossible d'installer yt-dlp: {e}")
            # Retourner un module factice pour éviter le crash
            return None

# Importer yt-dlp de manière sécurisée
yt_dlp = ensure_ytdlp()

# Fonction de téléchargement de secours
def download_video_fallback(url, output_dir):
    """Fonction de secours si yt-dlp n'est pas disponible"""
    import streamlit as st
    st.error("⚠️ yt-dlp n'est pas disponible. Veuillez utiliser des vidéos locales ou réessayer plus tard.")
    return None