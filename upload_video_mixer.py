"""
Upload Video Mixer Pro 🎬 - TikTok/Reels Edition
Interface Streamlit pour créer des vidéos verticales avec reconnaissance faciale
Version Upload Only - Sans téléchargement YouTube
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
    create_temp_directory, cleanup_temp_files, 
    save_uploaded_file, format_duration, estimate_processing_time,
    process_uploaded_videos, validate_uploaded_file
)
from face_detector import extract_face_encoding_from_image
from text_detector import download_east_model, load_text_detection_model
from video_extractor import extract_best_clips_with_face
from video_assembler import create_final_video_ultra_safe as create_final_video

# Configuration de la page
st.set_page_config(
    page_title="Upload Video Mixer Pro",
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
        15, 600, DEFAULT_SETTINGS['output_duration'],
        help="Cette durée sera ignorée si 'Adapter la durée à l'audio' est activé"
    )
    max_clips_per_video = st.slider(
        "Nombre max de clips par vidéo:", 
        1, 50, DEFAULT_SETTINGS['max_clips_per_video'],
        help="Augmentez pour plus de variété"
    )
    
with col2:
    min_clip_duration = st.slider(
        "Durée min d'un clip (secondes):", 
        2, 5, DEFAULT_SETTINGS['min_clip_duration']
    )
    max_clip_duration = st.slider(
        "Durée max d'un clip (secondes):", 
        5, 30, DEFAULT_SETTINGS['max_clip_duration']
    )

# Section 2: Reconnaissance faciale
st.header("2. Reconnaissance faciale (optionnel)")
st.write("Uploadez une photo de la personne à reconnaître dans les vidéos")

reference_image = st.file_uploader(
    "Photo de référence", 
    type=['jpg', 'jpeg', 'png']
)

target_face_encoding = None
if reference_image:
    # Sauvegarder et traiter l'image
    image_path = save_uploaded_file(reference_image, st.session_state.temp_dir, "reference.jpg")
    if image_path:
        target_face_encoding = extract_face_encoding_from_image(image_path)
        
        if target_face_encoding is not None:
            st.success(UI_MESSAGES['face_loaded'])
            
            # Ajouter un slider pour ajuster la sensibilité
            face_threshold = st.slider(
                "🎯 Sensibilité de la reconnaissance faciale",
                0.1, 1.0, 0.4, 0.05,
                help="Plus la valeur est basse, plus la reconnaissance est stricte. 0.4 = recommandé"
            )
        else:
            st.warning(UI_MESSAGES['face_not_detected'])
            face_threshold = 0.4
else:
    face_threshold = 0.4

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

# Options avancées
col1, col2 = st.columns(2)
with col1:
    shuffle_clips = st.checkbox(
        "Mélanger les clips aléatoirement", 
        value=DEFAULT_SETTINGS['shuffle_clips']
    )
    face_detection_only = st.checkbox(
        "Extraire UNIQUEMENT les clips avec le visage cible", 
        value=DEFAULT_SETTINGS['face_detection_only'],
        help="Si activé, seuls les clips où la personne est détectée seront inclus"
    )
    if face_detection_only and not reference_image:
        st.warning("⚠️ Cette option nécessite une photo de référence")
    smart_crop = st.checkbox(
        "🎯 Crop intelligent (centre sur les visages)", 
        value=DEFAULT_SETTINGS['smart_crop'],
        help="Centre automatiquement le cadrage sur les visages détectés"
    )
    force_diversity = st.checkbox(
        "🌈 Forcer la diversité des clips",
        value=True,
        help="Assure une distance minimale de 10 secondes entre les clips"
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
    exclude_first_seconds = st.slider(
        "Exclure les X premières secondes de chaque vidéo", 
        0, 10, 0,
        help="Utile pour éviter les intros, logos animés, etc."
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
        type=['mp3', 'wav', 'm4a', 'aac', 'ogg']
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
    if audio_file and 'audio_path' in audio_config:
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
        type=['jpg', 'jpeg', 'png']
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

# Section 5: Upload des vidéos
st.header("5. Upload des vidéos 📁")
st.write("Uploadez vos propres vidéos (formats supportés: MP4, MOV, AVI, WEBM, MKV)")

uploaded_videos = st.file_uploader(
    "Sélectionnez vos vidéos",
    type=['mp4', 'mov', 'avi', 'webm', 'mkv'],
    accept_multiple_files=True,
    help="Vous pouvez sélectionner plusieurs vidéos à la fois"
)

# Validation et affichage des fichiers uploadés
valid_videos = []
if uploaded_videos:
    st.subheader("📋 Fichiers uploadés")
    
    total_size = 0
    for video in uploaded_videos:
        if validate_uploaded_file(video):
            valid_videos.append(video)
            size_mb = video.size / 1024 / 1024
            total_size += size_mb
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"✅ {video.name}")
            with col2:
                st.write(f"{size_mb:.1f} MB")
            with col3:
                st.write(f"{video.type}")
    
    if valid_videos:
        st.info(f"📊 Total: {len(valid_videos)} fichier(s) valide(s) - {total_size:.1f} MB")
    else:
        st.error("❌ Aucun fichier valide sélectionné")

# Bouton de traitement
if st.button("🎬 Créer la vidéo TikTok/Reels", type="primary"):
    if not valid_videos:
        st.error("Veuillez uploader au moins une vidéo")
    else:
        st.header("6. Traitement")
        
        # Estimation du temps
        estimated_time = estimate_processing_time(
            len(valid_videos), 
            output_duration * len(valid_videos), 
            target_face_encoding is not None
        )
        st.info(f"⏱️ Temps estimé: {estimated_time}")
        
        # Traitement des vidéos uploadées
        with st.spinner("Traitement des vidéos uploadées..."):
            processed_files = process_uploaded_videos(valid_videos, st.session_state.temp_dir)
        
        if processed_files:
            # Résumé global du traitement
            st.markdown("### 📊 Résumé du traitement")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Vidéos traitées", len(processed_files))
            
            with col2:
                total_size = sum(f.get('file_size_mb', 0) for f in processed_files)
                st.metric("Taille totale", f"{total_size:.1f} MB")
            
            with col3:
                total_duration = sum(f.get('duration', 0) for f in processed_files)
                st.metric("Durée totale", format_duration(total_duration))
            
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
            
            # Extraction des clips (version originale)
            all_clips = []
            clips_by_video = {}
            
            st.subheader("Extraction des meilleurs moments")
            
            for idx, video_info in enumerate(processed_files):
                st.write(f"**Analyse de:** {video_info['title']} ({idx+1}/{len(processed_files)})")
                
                # GESTION MÉMOIRE: Traiter une vidéo à la fois
                try:
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
                        use_lanczos=use_lanczos,
                        exclude_first_seconds=exclude_first_seconds,
                        face_threshold=face_threshold
                    )
                    
                    clips_by_video[idx] = clips
                    all_clips.extend(clips)
                    
                    # Libération mémoire après chaque vidéo
                    import gc
                    gc.collect()
                    st.info(f"✅ Vidéo {idx+1} traitée - {len(clips)} clips extraits, mémoire libérée")
                    
                except Exception as e:
                    st.error(f"❌ Erreur traitement vidéo {idx+1}: {str(e)}")
                    clips_by_video[idx] = []
                    continue
            
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
                    st.metric("Vidéos analysées", len(processed_files))
                
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
                        
                        # Aperçu
                        st.video(output_path)
                        
                    # Nettoyage final
                    import gc
                    gc.collect()
                    st.success(f"✅ Traitement terminé - mémoire libérée")
                    
            else:
                st.error("Aucun clip n'a pu être extrait des vidéos")

# Nettoyage
if st.button("🗑️ Nettoyer les fichiers temporaires"):
    if cleanup_temp_files(st.session_state.temp_dir):
        st.session_state.temp_dir = create_temp_directory()
        st.success(UI_MESSAGES['temp_cleaned'])

# Footer
st.markdown("---")
st.markdown("🚀 Upload Video Mixer Pro - TikTok/Reels Edition")
st.markdown("Format vertical 9:16 | Upload de vidéos | Reconnaissance faciale | Modes d'analyse | Détection de texte")