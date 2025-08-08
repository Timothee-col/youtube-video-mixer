"""
Module de traitement vidéo principal
"""
import cv2
import numpy as np
import streamlit as st
import random
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, CompositeVideoClip, 
    ImageClip, AudioFileClip, afx
)
from PIL import Image
from typing import List, Dict, Optional, Tuple
from constants import VIDEO_FORMAT, DEFAULT_SETTINGS, UI_MESSAGES
from video_analyzer import analyze_video_segments_with_face
from face_detector import get_face_regions_for_crop
from text_detector import detect_text_regions, remove_text_with_crop, remove_text_with_inpainting

def resize_and_center_vertical(
    clip: VideoFileClip,
    remove_text_method: Optional[str] = None,
    text_net: Optional[cv2.dnn_Net] = None,
    face_regions: Optional[List[Dict]] = None,
    use_lanczos: bool = False  # Désactivé par défaut pour Railway
) -> VideoFileClip:
    """
    Redimensionne la vidéo au format vertical 9:16 avec crop intelligent
    
    Args:
        clip: Clip vidéo à traiter
        remove_text_method: Méthode de suppression de texte
        text_net: Modèle de détection de texte
        face_regions: Régions de visages pour le crop intelligent
        use_lanczos: Utiliser Lanczos pour un resize plus net
    
    Returns:
        VideoFileClip: Clip redimensionné
    """
    target_width = VIDEO_FORMAT['width']
    target_height = VIDEO_FORMAT['height']
    target_ratio = VIDEO_FORMAT['ratio']
    
    # Si on doit enlever le texte, le faire frame par frame
    if remove_text_method and text_net is not None:
        def process_frame(frame):
            text_regions = detect_text_regions(frame, text_net)
            
            if text_regions:
                if remove_text_method == "crop":
                    frame = remove_text_with_crop(frame, text_regions)
                elif remove_text_method == "inpaint":
                    frame = remove_text_with_inpainting(frame, text_regions)
            
            return frame
        
        clip = clip.fl_image(process_frame)
    
    # Dimensions originales
    orig_w, orig_h = clip.size
    orig_ratio = orig_w / orig_h
    
    # Fonction de resize avec Lanczos
    def apply_lanczos_resize(frame):
        """
        Applique un resize Lanczos de haute qualité à chaque frame
        """
        # Validation pour éviter les erreurs avec des frames None
        if frame is None:
            st.error("❌ Frame None détecté dans Lanczos resize!")
            # Retourner une frame noire de la bonne taille
            return np.zeros((target_height, target_width, 3), dtype=np.uint8)
        
        try:
            # Vérifier que la frame a la bonne forme
            if not isinstance(frame, np.ndarray) or len(frame.shape) != 3:
                st.error(f"❌ Frame invalide: type={type(frame)}, shape={getattr(frame, 'shape', 'N/A')}")
                return np.zeros((target_height, target_width, 3), dtype=np.uint8)
            
            # Utiliser cv2.INTER_LANCZOS4 pour la meilleure qualité
            result = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
            return result
        except Exception as e:
            st.error(f"❌ Erreur Lanczos resize: {str(e)}")
            return np.zeros((target_height, target_width, 3), dtype=np.uint8)
    
    # Si déjà au bon ratio
    if abs(orig_ratio - target_ratio) < 0.1:
        if use_lanczos:
            clip = clip.fl_image(apply_lanczos_resize)
        else:
            clip = clip.resize((target_width, target_height))
    
    # Si horizontal (plus large que haut)
    elif orig_ratio > target_ratio:
        new_height = orig_h
        new_width = int(orig_h * target_ratio)
        
        # Centrer sur les visages si disponibles
        if face_regions and len(face_regions) > 0:
            face_centers_x = [(r['x'] + r['width']//2) for r in face_regions]
            avg_x = sum(face_centers_x) // len(face_centers_x)
            x_start = avg_x - new_width // 2
            x_start = max(0, min(x_start, orig_w - new_width))
        else:
            x_start = (orig_w - new_width) // 2
        
        # Cropper d'abord
        clip = clip.crop(x1=x_start, y1=0, x2=x_start + new_width, y2=orig_h)
        
        # Puis resize avec Lanczos ou méthode standard
        if use_lanczos:
            clip = clip.fl_image(apply_lanczos_resize)
        else:
            clip = clip.resize((target_width, target_height))
    
    # Si trop vertical
    else:
        new_width = orig_w
        new_height = int(orig_w / target_ratio)
        
        # Garder les visages dans le cadre
        if face_regions and len(face_regions) > 0:
            face_tops = [r['y'] for r in face_regions]
            face_bottoms = [r['y'] + r['height'] for r in face_regions]
            min_y = min(face_tops)
            max_y = max(face_bottoms)
            
            face_center_y = (min_y + max_y) // 2
            y_start = face_center_y - new_height // 2
            
            if y_start < 0:
                y_start = 0
            elif y_start + new_height > orig_h:
                y_start = orig_h - new_height
            
            if max_y - min_y > new_height * 0.8:
                y_start = max(0, min_y - int(new_height * 0.1))
        else:
            y_start = (orig_h - new_height) // 2
        
        # Cropper d'abord
        clip = clip.crop(x1=0, y1=y_start, x2=orig_w, y2=y_start + new_height)
        
        # Puis resize avec Lanczos ou méthode standard
        if use_lanczos:
            clip = clip.fl_image(apply_lanczos_resize)
        else:
            clip = clip.resize((target_width, target_height))
    
    # Retirer l'audio
    clip = clip.without_audio()
    
    return clip

def extract_best_clips_with_face(
    video_path: str,
    target_face_encoding: Optional[np.ndarray] = None,
    max_clips_per_video: int = 3,
    min_clip_duration: float = 3,
    max_clip_duration: float = 8,
    video_index: int = 0,
    analysis_mode: str = "🎯 Précis (3-5 min)",
    avoid_text: bool = False,
    text_net: Optional[cv2.dnn_Net] = None,
    face_detection_only: bool = False,
    remove_text_method: Optional[str] = None,
    smart_crop: bool = True,
    use_lanczos: bool = False,  # Désactivé pour économiser la mémoire sur Railway
    exclude_first_seconds: float = 0,
    face_threshold: float = 0.4
) -> List[VideoFileClip]:
    """
    Extrait les meilleurs clips d'une vidéo
    
    Args:
        video_path: Chemin de la vidéo
        target_face_encoding: Encoding du visage cible
        max_clips_per_video: Nombre max de clips
        min_clip_duration: Durée min d'un clip
        max_clip_duration: Durée max d'un clip
        video_index: Index de la vidéo
        analysis_mode: Mode d'analyse
        avoid_text: Éviter le texte
        text_net: Modèle de détection de texte
        face_detection_only: Extraire uniquement avec visage cible
        remove_text_method: Méthode de suppression de texte
        smart_crop: Crop intelligent sur les visages
    
    Returns:
        List[VideoFileClip]: Liste des clips extraits
    """
    video = VideoFileClip(video_path)
    duration = video.duration
    
    # Analyser la vidéo
    best_segments = analyze_video_segments_with_face(
        video_path,
        target_face_encoding=target_face_encoding,
        min_clip_duration=min_clip_duration,
        max_clip_duration=max_clip_duration,
        video_index=video_index,
        analysis_mode=analysis_mode,
        avoid_text=avoid_text,
        text_net=text_net,
        remove_text_method=remove_text_method,
        exclude_first_seconds=exclude_first_seconds,
        face_threshold=face_threshold
    )
    
    clips = []
    
    for i, segment in enumerate(best_segments[:max_clips_per_video]):
        # Filtrer si nécessaire
        if face_detection_only and target_face_encoding is not None:
            if not segment.get('has_target_face', False):
                st.info(f"🚫 Segment {i+1} ignoré: pas de visage cible")
                continue
        
        try:
            # Vérifications
            if segment['start'] >= duration:
                st.warning(f"Clip {i+1} ignoré: début après la fin de la vidéo")
                continue
            
            if segment['end'] > duration:
                segment['end'] = duration
            
            actual_start = max(0, segment['start'])
            actual_end = min(segment['end'], duration)
            
            if actual_end > actual_start and actual_end - actual_start >= 1:
                clip = video.subclip(actual_start, actual_end)
                
                # Détection des visages pour le crop intelligent
                face_regions = []
                if smart_crop:
                    try:
                        frame = clip.get_frame(0.1)
                        face_regions = get_face_regions_for_crop(frame, target_face_encoding, face_threshold)
                        
                        if face_regions:
                            st.success(f"   🎯 {len(face_regions)} visage(s) détecté(s) pour le crop intelligent")
                    except Exception as e:
                        st.warning(f"   ⚠️ Crop intelligent désactivé: {str(e)}")
                
                # Convertir au format vertical
                try:
                    # Vérifier que le clip est valide avant le resize
                    if clip is None or not hasattr(clip, 'get_frame'):
                        st.error(f"❌ Clip {i+1} invalide avant resize")
                        continue
                    
                    # Tester l'accès à une frame pour valider le clip
                    try:
                        test_frame = clip.get_frame(0)
                        if test_frame is None:
                            st.error(f"❌ Clip {i+1} retourne des frames None")
                            clip.close()
                            continue
                    except Exception as e:
                        st.error(f"❌ Impossible d'accéder aux frames du clip {i+1}: {str(e)}")
                        clip.close()
                        continue
                    
                    clip = resize_and_center_vertical(
                        clip,
                        remove_text_method=remove_text_method if remove_text_method else None,
                        text_net=text_net if remove_text_method else None,
                        face_regions=face_regions if smart_crop else None,
                        use_lanczos=use_lanczos
                    )
                    
                    # Valider le clip avant de l'ajouter
                    if clip is not None and hasattr(clip, 'duration') and clip.duration > 0:
                        clips.append(clip)
                    else:
                        st.warning(f"⚠️ Clip {i+1} invalide après conversion, ignoré")
                        if clip:
                            clip.close()
                except Exception as e:
                    st.error(f"❌ Erreur conversion clip {i+1}: {str(e)}")
                    if 'clip' in locals() and clip:
                        try:
                            clip.close()
                        except:
                            pass
                
                # Afficher les infos
                face_indicator = "👤" if segment.get('has_target_face', False) else ""
                text_indicator = "📝" if avoid_text and text_net is not None else ""
                st.info(f"📹 Clip {i+1}: {segment['start']:.1f}s - {segment['end']:.1f}s (Score: {segment['score']:.0f}) {face_indicator} {text_indicator}")
                
        except Exception as e:
            st.warning(f"Impossible d'extraire le clip {i+1}: {str(e)}")
    
    return clips

def add_logo_overlay(
    video: VideoFileClip,
    logo_path: str,
    position: str = "Haut gauche",
    size_percent: int = 20,
    opacity: float = 0.5,
    margin: int = 40,
    vertical_position: int = 10
) -> VideoFileClip:
    """
    Ajoute un logo en overlay sur la vidéo
    
    Args:
        video: Vidéo de base
        logo_path: Chemin du logo
        position: Position du logo
        size_percent: Taille en % de la largeur
        opacity: Opacité du logo
        margin: Marge horizontale
        vertical_position: Position verticale
    
    Returns:
        VideoFileClip: Vidéo avec logo
    """
    try:
        # Charger et redimensionner le logo
        logo_img = Image.open(logo_path)
        video_width = VIDEO_FORMAT['width']
        logo_width = int(video_width * size_percent / 100)
        logo_height = int(logo_img.height * (logo_width / logo_img.width))
        
        # Créer le clip du logo
        logo_clip = ImageClip(logo_path).resize((logo_width, logo_height))
        logo_clip = logo_clip.set_duration(video.duration)
        logo_clip = logo_clip.set_opacity(opacity)
        
        # Positionner le logo
        if position == "Haut gauche":
            logo_clip = logo_clip.set_position((margin, vertical_position))
        elif position == "Haut droite":
            logo_clip = logo_clip.set_position((video_width - logo_width - margin, vertical_position))
        else:  # Haut centre
            logo_clip = logo_clip.set_position(((video_width - logo_width) // 2, vertical_position))
        
        # Composer
        video = CompositeVideoClip([video, logo_clip])
        st.success("✅ Logo ajouté en overlay!")
        
    except Exception as e:
        st.warning(f"⚠️ Impossible d'ajouter le logo: {str(e)}")
    
    return video

def add_audio_to_video(
    video: VideoFileClip,
    audio_path: str,
    volume: float = 1.0,
    fade_in: float = 1.0,
    fade_out: float = 1.0,
    adapt_to_audio: bool = False,
    extra_seconds: int = 0
) -> VideoFileClip:
    """
    Ajoute une piste audio à la vidéo
    
    Args:
        video: Vidéo de base
        audio_path: Chemin de l'audio
        volume: Volume de l'audio
        fade_in: Durée du fondu d'entrée
        fade_out: Durée du fondu de sortie
        adapt_to_audio: Adapter la durée de la vidéo à l'audio
        extra_seconds: Secondes supplémentaires après l'audio
    
    Returns:
        VideoFileClip: Vidéo avec audio
    """
    try:
        # Charger l'audio
        audio_clip = AudioFileClip(audio_path)
        
        # Ajuster le volume
        audio_clip = audio_clip.volumex(volume)
        
        # Appliquer les fondus
        if fade_in > 0:
            audio_clip = audio_clip.audio_fadein(fade_in)
        if fade_out > 0:
            audio_clip = audio_clip.audio_fadeout(fade_out)
        
        # Gérer la durée
        video_duration = video.duration
        audio_duration = audio_clip.duration
        
        if adapt_to_audio:
            target_duration = audio_duration + extra_seconds
            
            if video_duration < target_duration:
                # Boucler la vidéo
                n_loops = int(target_duration / video_duration) + 1
                video_clips = [video] * n_loops
                looped_video = concatenate_videoclips(video_clips)
                video = looped_video.subclip(0, target_duration)
                st.info(f"🔄 Vidéo ajustée à {target_duration:.1f}s")
            elif video_duration > target_duration:
                # Couper la vidéo
                video = video.subclip(0, target_duration)
                st.info(f"✂️ Vidéo coupée à {target_duration:.1f}s")
        else:
            # Adapter l'audio à la vidéo
            if audio_clip.duration > video_duration:
                audio_clip = audio_clip.subclip(0, video_duration)
                st.info("✂️ Audio coupé à la durée de la vidéo")
        
        # Attacher l'audio
        video = video.set_audio(audio_clip)
        st.success("✅ Audio ajouté avec succès!")
        
    except Exception as e:
        st.warning(f"⚠️ Impossible d'ajouter l'audio: {str(e)}")
        video = video.without_audio()
    
    return video

def create_final_video(
    clips: List[VideoFileClip],
    output_path: str,
    shuffle: bool = True,
    smart_shuffle: bool = True,
    clips_by_video: Optional[Dict[int, List[VideoFileClip]]] = None,
    logo_config: Optional[Dict] = None,
    audio_config: Optional[Dict] = None,
    tagline_path: Optional[str] = None,
    output_duration: Optional[float] = None
) -> bool:
    """
    Crée la vidéo finale à partir des clips (optimisé pour Railway)
    
    Args:
        clips: Liste des clips
        output_path: Chemin de sortie
        shuffle: Mélanger les clips
        smart_shuffle: Mélange intelligent
        clips_by_video: Clips groupés par vidéo
        logo_config: Configuration du logo
        audio_config: Configuration audio
        tagline_path: Chemin de la tagline
        output_duration: Durée souhaitée
    
    Returns:
        bool: True si succès
    """
    import gc  # Garbage collector pour libérer la mémoire
    
    try:
        st.warning("⚠️ Mode économie mémoire activé pour Railway")
        
        # Limiter le nombre de clips pour éviter l'OOM
        MAX_CLIPS_RAILWAY = 10
        if len(clips) > MAX_CLIPS_RAILWAY:
            st.warning(f"⚠️ Limitation à {MAX_CLIPS_RAILWAY} clips pour économiser la mémoire")
            clips = clips[:MAX_CLIPS_RAILWAY]
        
        # Mélanger les clips si demandé
        if smart_shuffle and clips_by_video and len(clips_by_video) > 1:
            clips = smart_shuffle_clips(clips_by_video)
            st.info("🤖 Mélange intelligent appliqué")
        elif shuffle:
            random.shuffle(clips)
            st.info("🔀 Clips mélangés aléatoirement")
        
        # Valider et optimiser les clips
        st.info("🔍 Validation des clips...")
        valid_clips = []
        for i, clip in enumerate(clips):
            # Vérifier que le clip est valide
            if clip is None:
                st.warning(f"⚠️ Clip {i+1} est None, ignoré")
                continue
            
            try:
                # Tester l'accès au clip
                if hasattr(clip, 'duration') and clip.duration > 0:
                    # S'assurer que le clip n'a pas d'audio (économie mémoire)
                    if hasattr(clip, 'audio') and clip.audio is not None:
                        clip = clip.without_audio()
                    valid_clips.append(clip)
                    st.success(f"✅ Clip {i+1} validé ({clip.duration:.1f}s)")
                else:
                    st.warning(f"⚠️ Clip {i+1} invalide (durée: {getattr(clip, 'duration', 'N/A')})")
                    if clip:
                        clip.close()
            except Exception as e:
                st.error(f"❌ Erreur validation clip {i+1}: {str(e)}")
                if clip:
                    try:
                        clip.close()
                    except:
                        pass
        
        if not valid_clips:
            st.error("❌ Aucun clip valide trouvé!")
            return False
            
        st.info(f"✅ {len(valid_clips)} clips valides sur {len(clips)}")
        optimized_clips = valid_clips
        
        # Force garbage collection
        gc.collect()
        
        # Concaténer par petits groupes pour économiser la mémoire
        st.info("🔗 Assemblage optimisé des clips...")
        if len(optimized_clips) > 5:
            # Traiter par groupes de 5
            temp_videos = []
            for i in range(0, len(optimized_clips), 5):
                group = optimized_clips[i:i+5]
                temp_video = concatenate_videoclips(group, method="compose")
                temp_videos.append(temp_video)
                # Libérer les clips du groupe
                for clip in group:
                    clip.close()
                gc.collect()
            
            # Assembler les vidéos temporaires
            final_video = concatenate_videoclips(temp_videos, method="compose")
            # Libérer les vidéos temporaires
            for temp in temp_videos:
                temp.close()
        else:
            final_video = concatenate_videoclips(optimized_clips, method="compose")
        
        # Ajuster la durée si nécessaire
        if output_duration and not (audio_config and audio_config.get('adapt_to_audio')):
            if final_video.duration > output_duration:
                final_video = final_video.subclip(0, output_duration)
                st.info(f"✂️ Vidéo coupée à {output_duration}s")
        
        # Ajouter le logo
        if logo_config:
            final_video = add_logo_overlay(final_video, **logo_config)
        
        # Ajouter l'audio
        if audio_config:
            final_video = add_audio_to_video(final_video, **audio_config)
        else:
            final_video = final_video.without_audio()
        
        # Ajouter la tagline
        if tagline_path:
            final_video = add_tagline(final_video, tagline_path)
        
        # Sauvegarder avec optimisations pour Railway
        st.info("🎬 Encodage de la vidéo finale... (peut prendre 2-5 minutes)")
        
        # Optimisations pour Railway - Balance entre qualité et mémoire
        encoding_params = {
            'codec': 'libx264',
            'fps': VIDEO_FORMAT['fps'],
            'preset': 'faster',  # Balance entre vitesse et compression
            'threads': 4,  # Moins de threads = moins de RAM
            'logger': 'bar',  # Afficher la progression
            'write_logfile': False,  # Économise la mémoire
        }
        
        # Réduire la qualité si la vidéo est longue (pour éviter timeout)
        if final_video.duration > 60:
            encoding_params['bitrate'] = '2000k'  # Qualité réduite
            st.warning("⚠️ Qualité réduite pour optimiser le temps d'encodage")
        else:
            encoding_params['bitrate'] = VIDEO_FORMAT['bitrate']
        
        if final_video.audio is not None:
            encoding_params['audio_codec'] = 'aac'
            encoding_params['audio_bitrate'] = '128k'  # Audio optimisé
        else:
            encoding_params['audio'] = False
            
        # Progress tracking
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        def progress_callback(frame, total_frames):
            if total_frames > 0:
                progress = int((frame / total_frames) * 100)
                progress_bar.progress(progress)
                progress_text.text(f"Encodage: {progress}%")
        
        # Écrire la vidéo
        final_video.write_videofile(
            output_path,
            **encoding_params,
            temp_audiofile=output_path.replace('.mp4', '_temp_audio.m4a')
        )
        
        progress_bar.progress(100)
        progress_text.text("✅ Encodage terminé!")
        
        # Libérer la mémoire
        for clip in clips:
            clip.close()
        final_video.close()
        
        return True
        
    except Exception as e:
        st.error(f"Erreur lors de la création de la vidéo: {str(e)}")
        return False

def smart_shuffle_clips(clips_by_video: Dict[int, List[VideoFileClip]]) -> List[VideoFileClip]:
    """
    Mélange intelligent en alternant entre les vidéos
    
    Args:
        clips_by_video: Clips groupés par vidéo
    
    Returns:
        List[VideoFileClip]: Clips mélangés
    """
    shuffled_clips = []
    
    # Créer des listes de clips par vidéo
    video_clip_lists = list(clips_by_video.values())
    
    # Mélanger chaque liste individuellement
    for clip_list in video_clip_lists:
        random.shuffle(clip_list)
    
    # Alterner entre les vidéos
    max_clips = max(len(clips) for clips in video_clip_lists)
    
    for i in range(max_clips):
        for video_clips in video_clip_lists:
            if i < len(video_clips):
                shuffled_clips.append(video_clips[i])
    
    return shuffled_clips

def add_tagline(video: VideoFileClip, tagline_path: str) -> VideoFileClip:
    """
    Ajoute une vidéo tagline à la fin
    
    Args:
        video: Vidéo principale
        tagline_path: Chemin de la tagline
    
    Returns:
        VideoFileClip: Vidéo avec tagline
    """
    try:
        st.info("🏷️ Ajout de la vidéo tagline...")
        tagline_clip = VideoFileClip(tagline_path)
        
        # Redimensionner au format 9:16
        tagline_clip = resize_and_center_vertical(tagline_clip, use_lanczos=False)
        
        # Si la vidéo a un audio, garder la tagline sans audio
        if video.audio is not None:
            tagline_clip = tagline_clip.without_audio()
        
        # Concaténer
        final_video = concatenate_videoclips([video, tagline_clip], method="compose")
        st.success(f"✅ Tagline ajoutée ({tagline_clip.duration:.1f}s)")
        
        return final_video
        
    except Exception as e:
        st.warning(f"⚠️ Impossible d'ajouter la tagline: {str(e)}")
        return video