"""
YouTube Video Mixer Pro 🎬 - TikTok/Reels Edition
Interface Streamlit pour créer des vidéos verticales avec reconnaissance faciale
"""
import streamlit as st
import os
import tempfile
from typing import List, Dict, Optional

# Import des modules
from constants import (
    UI_MESSAGES, DEFAULT_SETTINGS, ANALYSIS_MODES, 
    SUPPORTED_EXTENSIONS, VIDEO_FORMAT
)
from utils import (
    create_temp_directory, cleanup_temp_files, download_youtube_videos,
    save_uploaded_file, format_duration, estimate_processing_time
)
from face_detector import extract_face_encoding_from_image
from text_detector import download_east_model, load_text_detection_model
from video_processor import (
    extract_best_clips_with_face, create_final_video
)

# Configuration de la page
st.set_page_config(
    page_title="YouTube Video Mixer Pro",
    page_icon="🎬",
    layout="wide"
)

# Initialisation de la session
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = create_temp_directory()

# Interface principale
st.title(UI_MESSAGES['app_title'])
st.write(UI_MESSAGES['app_subtitle'])

# Section 1: Configuration
st.header("1. Configuration")

col1, col2 = st.columns(2)
with col1:
    output_duration = st.slider(
        "Durée totale de sortie (secondes):", 
        15, 120, DEFAULT_SETTINGS['output_duration'],
        help="Cette durée sera ignorée si 'Adapter la durée à l'audio' est activé"
    )
    max_clips_per_video = st.slider(
        "Nombre max de clips par vidéo:", 
        1, 5, DEFAULT_SETTINGS['max_clips_per_video']
    )
    
with col2:
    min_clip_duration = st.slider(
        "Durée min d'un clip (secondes):", 
        2, 5, DEFAULT_SETTINGS['min_clip_duration']
    )
    max_clip_duration = st.slider(
        "Durée max d'un clip (secondes):", 
        5, 15, DEFAULT_SETTINGS['max_clip_duration']
    )

# Section 2: Reconnaissance faciale
st.header("2. Reconnaissance faciale (optionnel)")
st.write("Uploadez une photo de la personne à reconnaître dans les vidéos")

reference_image = st.file_uploader(
    "Photo de référence", 
    type=SUPPORTED_EXTENSIONS['image']
)

target_face_encoding = None
if reference_image:
    # Sauvegarder et traiter l'image
    image_path = save_uploaded_file(reference_image, st.session_state.temp_dir, "reference.jpg")
    if image_path:
        target_face_encoding = extract_face_encoding_from_image(image_path)
        
        if target_face_encoding is not None:
            st.success(UI_MESSAGES['face_loaded'])
        else:
            st.warning(UI_MESSAGES['face_not_detected'])

# Mode d'analyse
analysis_mode = st.radio(
    "Mode d'analyse:",
    list(ANALYSIS_MODES.keys()),
    index=1  # Précis par défaut
)

# Section qualité
with st.expander("🎨 Options de qualité", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        use_lanczos = st.checkbox(
            "🔍 Utiliser Lanczos (resize haute qualité)", 
            value=True,
            help="Améliore nettement la qualité du redimensionnement mais plus lent"
        )
        if use_lanczos:
            st.info("✨ Lanczos activé : meilleure netteté")
    with col2:
        st.write("📊 Comparaison:")
        st.write("- Standard : Rapide mais flou")
        st.write("- Lanczos : Plus net, +20% temps")
    
    # Nouvelle option de qualité de téléchargement
    st.markdown("### 📥 Qualité de téléchargement YouTube")
    download_quality = st.select_slider(
        "Sélectionnez la qualité de téléchargement:",
        options=['fast', 'standard', 'high', 'ultra'],
        value='high',
        format_func=lambda x: {
            'fast': '⚡ Rapide (720p min)',
            'standard': '📹 Standard (1080p)',
            'high': '🎯 Haute qualité (1080p+)',
            'ultra': '🚀 Ultra (meilleure disponible)'
        }[x]
    )
    
    if download_quality == 'ultra':
        st.warning("⚠️ Le mode Ultra peut prendre beaucoup plus de temps et d'espace disque")
    
    show_formats = st.checkbox(
        "📊 Afficher les formats disponibles lors du téléchargement",
        value=False,
        help="Voir les formats vidéo disponibles pour chaque URL YouTube"
    )

# Options avancées
col1, col2 = st.columns(2)
with col1:
    shuffle_clips = st.checkbox(
        "Mélanger les clips aléatoirement", 
        value=DEFAULT_SETTINGS['shuffle_clips']
    )
    face_detection_only = st.checkbox(
        "Extraire UNIQUEMENT les clips avec le visage cible", 
        value=DEFAULT_SETTINGS['face_detection_only']
    )
    smart_crop = st.checkbox(
        "🎯 Crop intelligent (centre sur les visages)", 
        value=DEFAULT_SETTINGS['smart_crop'],
        help="Centre automatiquement le cadrage sur les visages détectés"
    )
with col2:
    smart_shuffle = st.checkbox(
        "Mélange intelligent (alterne les sources)", 
        value=DEFAULT_SETTINGS['smart_shuffle']
    )
    exclude_last_seconds = st.slider(
        "Exclure les X dernières secondes de chaque vidéo", 
        0, 10, DEFAULT_SETTINGS['exclude_last_seconds']
    )

# Gestion du texte
avoid_text = st.checkbox(
    "🚫 Gérer le texte superposé (logos, titres, sous-titres, etc.)", 
    value=DEFAULT_SETTINGS['avoid_text']
)

remove_text_method = None
if avoid_text:
    text_removal_method = st.radio(
        "Méthode de gestion du texte:",
        [
            "🚫 Éviter les segments avec du texte",
            "✂️ Recadrer pour exclure le texte (Crop/Zoom)",
            "🎨 Effacer le texte (Inpainting)"
        ],
        index=0
    )
    
    if text_removal_method == "🚫 Éviter les segments avec du texte":
        st.info("🔍 Les segments avec du texte seront évités")
        remove_text_method = None
    elif text_removal_method == "✂️ Recadrer pour exclure le texte (Crop/Zoom)":
        st.info("✂️ L'image sera recadrée pour exclure les zones de texte")
        remove_text_method = "crop"
    else:
        st.info("🎨 Le texte sera effacé avec l'inpainting (plus lent mais meilleur résultat)")
        remove_text_method = "inpaint"

# Section 3: Audio
st.header("3. Bande son / Voix off 🎙️")
st.write("Ajoutez une narration, voix off ou musique de fond à votre vidéo")

audio_config = {}
col1, col2 = st.columns(2)
with col1:
    audio_file = st.file_uploader(
        "🎙️ Fichier audio (MP3, WAV, M4A) - Voix off, narration ou musique", 
        type=SUPPORTED_EXTENSIONS['audio']
    )
    if audio_file:
        audio_path = save_uploaded_file(
            audio_file, 
            st.session_state.temp_dir, 
            f"soundtrack.{audio_file.name.split('.')[-1]}"
        )
        if audio_path:
            st.success("✅ Fichier audio chargé!")
            audio_config['audio_path'] = audio_path
        
with col2:
    if audio_file and audio_path:
        audio_config['volume'] = st.slider("Volume de l'audio:", 0.0, 2.0, 1.0, 0.1)
        audio_config['fade_in'] = st.slider("Fondu d'entrée (secondes):", 0.0, 5.0, 1.0, 0.5)
        audio_config['fade_out'] = st.slider("Fondu de sortie (secondes):", 0.0, 5.0, 1.0, 0.5)
        audio_config['adapt_to_audio'] = st.checkbox(
            "🎯 Adapter la durée de la vidéo à l'audio", 
            value=False,
            help="La vidéo sera ajustée exactement à la durée de l'audio"
        )
        if audio_config['adapt_to_audio']:
            audio_config['extra_seconds'] = st.slider(
                "Secondes de vidéo après la fin de l'audio:", 
                0, 10, 0,
                help="Secondes supplémentaires AVANT la tagline"
            )

# Section 4: Personnalisation
st.header("4. Personnalisation de la marque")
st.write("Ajoutez votre identité visuelle à la vidéo finale")

logo_config = {}
tagline_path = None

col1, col2 = st.columns(2)
with col1:
    tagline_video = st.file_uploader(
        "📹 Vidéo tagline (MP4) - sera ajoutée à la fin", 
        type=['mp4', 'mov']
    )
    if tagline_video:
        tagline_path = save_uploaded_file(tagline_video, st.session_state.temp_dir, "tagline.mp4")
        if tagline_path:
            st.success("✅ Vidéo tagline chargée!")
        
with col2:
    logo_image = st.file_uploader(
        "🖼️ Logo (PNG/JPG) - sera affiché en overlay", 
        type=SUPPORTED_EXTENSIONS['image']
    )
    if logo_image:
        logo_config['position'] = st.selectbox(
            "Position du logo:",
            ["Haut gauche", "Haut droite", "Haut centre"]
        )
        logo_config['size_percent'] = st.slider("Taille du logo (% de la largeur):", 10, 50, 20)
        logo_config['opacity'] = st.slider("Opacité du logo:", 0.0, 1.0, 0.5, 0.05)
        logo_config['margin'] = st.slider("Marge depuis le bord horizontal (pixels):", -50, 200, 40)
        logo_config['vertical_position'] = st.slider("Position verticale (pixels depuis le haut):", -50, 300, 0)
        
        st.info(f"🔍 Aperçu: Logo à {logo_config['vertical_position']}px du haut, opacité {logo_config['opacity']:.0%}")
        
        logo_path = save_uploaded_file(logo_image, st.session_state.temp_dir, "logo.png")
        if logo_path:
            logo_config['logo_path'] = logo_path
            st.success("✅ Logo chargé!")

# Section 5: URLs YouTube
st.header("5. URLs YouTube")
urls = st.text_area(
    "Entrez les URLs YouTube (une par ligne):", 
    height=150,
    placeholder="https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=..."
)

# Bouton de traitement
if st.button("🎬 Créer la vidéo TikTok/Reels", type="primary"):
    if not urls:
        st.error("Veuillez entrer au moins une URL YouTube")
    else:
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        
        st.header("6. Traitement")
        
        # Estimation du temps
        estimated_time = estimate_processing_time(
            len(url_list), 
            output_duration * len(url_list), 
            analysis_mode
        )
        st.info(f"⏱️ Temps estimé: {format_duration(estimated_time)}")
        
        # Téléchargement des vidéos
        with st.spinner("Téléchargement des vidéos..."):
            # Mapper les options de qualité
            quality_mapping = {
                'fast': 'fast',
                'standard': 'standard', 
                'high': 'high',
                'ultra': 'ultra'
            }
            
            downloaded_files = download_youtube_videos(
                url_list, 
                st.session_state.temp_dir,
                quality_mode=quality_mapping.get(download_quality, 'high'),
                show_formats=show_formats if 'show_formats' in locals() else False
            )
        
        if downloaded_files:
            # Résumé global du téléchargement
            st.markdown("### 📊 Résumé du téléchargement")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Vidéos téléchargées", len(downloaded_files))
            
            with col2:
                total_size = sum(f.get('file_size_mb', 0) for f in downloaded_files)
                st.metric("Taille totale", f"{total_size:.1f} MB")
            
            with col3:
                valid_bitrates = [int(f.get('bitrate', 0)) for f in downloaded_files if f.get('bitrate') != 'N/A' and f.get('bitrate')]
                avg_bitrate = sum(valid_bitrates) / len(valid_bitrates) if valid_bitrates else 0
                st.metric("Bitrate moyen", f"{avg_bitrate:.0f} kbps" if avg_bitrate > 0 else "N/A")
            
            with col4:
                hd_count = sum(1 for f in downloaded_files if int(f.get('resolution', '0x0').split('x')[1]) >= 1080)
                st.metric("Vidéos HD (1080p+)", f"{hd_count}/{len(downloaded_files)}")
            
            st.markdown("---")
            # Charger le modèle de détection de texte si nécessaire
            text_net = None
            if avoid_text:
                model_path = download_east_model(st.session_state.temp_dir)
                if model_path:
                    text_net = load_text_detection_model(model_path)
                    if text_net:
                        st.success(UI_MESSAGES['text_model_loaded'])
                    else:
                        avoid_text = False
            
            # Extraction des clips
            all_clips = []
            clips_by_video = {}
            
            st.subheader("Extraction des meilleurs moments")
            
            for idx, video_info in enumerate(downloaded_files):
                st.write(f"**Analyse de:** {video_info['title']}")
                
                clips = extract_best_clips_with_face(
                    video_info['path'],
                    target_face_encoding=target_face_encoding,
                    max_clips_per_video=max_clips_per_video,
                    min_clip_duration=min_clip_duration,
                    max_clip_duration=max_clip_duration,
                    video_index=idx,
                    analysis_mode=analysis_mode,
                    avoid_text=avoid_text,
                    text_net=text_net,
                    face_detection_only=face_detection_only,
                    remove_text_method=remove_text_method,
                    smart_crop=smart_crop,
                    use_lanczos='use_lanczos' in locals() and use_lanczos
                )
                
                clips_by_video[idx] = clips
                all_clips.extend(clips)
            
            if all_clips:
                # Résumé
                st.subheader("📊 Résumé de l'extraction")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Clips extraits", len(all_clips))
                with col2:
                    clips_with_face = sum(1 for clip_list in clips_by_video.values() for _ in clip_list)
                    st.metric("Clips avec visage", clips_with_face)
                with col3:
                    st.metric("Vidéos analysées", len(downloaded_files))
                
                # Création de la vidéo finale
                with st.spinner("Assemblage de la vidéo finale (format vertical 9:16)..."):
                    output_path = os.path.join(st.session_state.temp_dir, "tiktok_reels_mix.mp4")
                    
                    success = create_final_video(
                        all_clips,
                        output_path,
                        shuffle=shuffle_clips,
                        smart_shuffle=smart_shuffle,
                        clips_by_video=clips_by_video if smart_shuffle else None,
                        logo_config=logo_config if logo_config.get('logo_path') else None,
                        audio_config=audio_config if audio_config.get('audio_path') else None,
                        tagline_path=tagline_path,
                        output_duration=output_duration
                    )
                    
                    if success:
                        st.success(UI_MESSAGES['video_created'])
                        st.balloons()
                        
                        # Statistiques finales
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Nombre de clips", len(all_clips))
                        with col2:
                            st.metric("Format", f"{VIDEO_FORMAT['width']}x{VIDEO_FORMAT['height']} HD")
                        with col3:
                            st.metric("FPS", VIDEO_FORMAT['fps'])
                        
                        # Téléchargement
                        with open(output_path, 'rb') as f:
                            st.download_button(
                                label="⬇️ Télécharger la vidéo TikTok/Reels",
                                data=f,
                                file_name="tiktok_reels_mix.mp4",
                                mime="video/mp4"
                            )
                        
                        # Amélioration vidéo si activée
                        if 'enhance_video' in locals() and enhance_video:
                            enhanced_output_path = output_path.replace('.mp4', '_enhanced.mp4')
                            
                            with st.spinner("🎨 Amélioration de la vidéo en cours..."):
                                if enhancement_method == "🚀 Real-ESRGAN (IA)" and check_realesrgan_installed():
                                    enhancement_success = enhance_video_with_realesrgan(
                                        video_path=output_path,
                                        output_path=enhanced_output_path,
                                        model_name=model_name,
                                        scale=scale,
                                        tile_size=tile_size,
                                        face_enhance=face_enhance,
                                        gpu_id=gpu_id,
                                        temp_dir=st.session_state.temp_dir
                                    )
                                else:
                                    # Méthode OpenCV
                                    enhancement_success = enhance_video_simple(
                                        video_path=output_path,
                                        output_path=enhanced_output_path,
                                        enhancement_level=enhancement_level,
                                        denoise=denoise,
                                        sharpen=sharpen,
                                        brightness=brightness,
                                        contrast=contrast,
                                        saturation=saturation
                                    )
                                
                                if enhancement_success:
                                    # Remplacer le fichier original par la version améliorée
                                    os.remove(output_path)
                                    os.rename(enhanced_output_path, output_path)
                                    st.success("✨ Vidéo améliorée avec succès!")
                                    
                                    # Afficher les statistiques
                                    import os
                                    file_size = os.path.getsize(output_path) / (1024 * 1024)  # En MB
                                    st.info(f"📊 Taille finale: {file_size:.1f} MB")
                        
                        # Aperçu
                        st.video(output_path)
            else:
                st.error("Aucun clip n'a pu être extrait des vidéos")

# Nettoyage
if st.button("🗑️ Nettoyer les fichiers temporaires"):
    if cleanup_temp_files(st.session_state.temp_dir):
        st.session_state.temp_dir = create_temp_directory()
        st.success(UI_MESSAGES['temp_cleaned'])

# Footer
st.markdown("---")
st.markdown("🚀 YouTube Video Mixer Pro - TikTok/Reels Edition")
st.markdown("Format vertical 9:16 | Téléchargement haute qualité | Reconnaissance faciale | Modes d'analyse | Détection de texte")