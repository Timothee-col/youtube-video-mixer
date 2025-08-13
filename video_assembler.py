"""
Module d'ASSEMBLAGE de vidéo avec concaténation ultra-robuste
==============================================================
Ce module gère l'assemblage final des clips extraits en une vidéo complète.
Utilise une méthode de matérialisation systématique pour éviter les erreurs MoviePy.

Fonctions principales :
- create_final_video_ultra_safe : Crée la vidéo finale avec tous les éléments
- safe_concatenate_with_materialization : Concaténation sécurisée des clips
- materialize_clip : Matérialise un clip sur disque pour éviter les références cassées
- smart_shuffle_clips : Mélange intelligent en alternant les sources
"""
import cv2
import numpy as np
import streamlit as st
import random
import time
import os
import tempfile
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, CompositeVideoClip, 
    ImageClip, AudioFileClip, afx
)
from PIL import Image
from typing import List, Dict, Optional, Tuple
from constants import VIDEO_FORMAT, DEFAULT_SETTINGS, UI_MESSAGES, IS_RAILWAY
from video_analyzer import analyze_video_segments_with_face
from video_normalizer import prepare_clips_for_concatenation, verify_clips_compatibility
from face_detector import get_face_regions_for_crop
from text_detector import detect_text_regions, remove_text_with_crop, remove_text_with_inpainting


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


def materialize_clip(clip: VideoFileClip, name: str = "clip") -> Optional[VideoFileClip]:
    """
    Matérialise un clip en l'écrivant sur disque puis en le rechargeant.
    Cela résout les problèmes de références cassées dans MoviePy.
    
    Args:
        clip: Le clip à matérialiser
        name: Nom pour identifier le clip dans les logs
    
    Returns:
        VideoFileClip matérialisé ou None si échec
    """
    if clip is None:
        st.error(f"❌ {name}: clip est None")
        return None
    
    try:
        # Créer un fichier temporaire unique
        temp_path = os.path.join(tempfile.gettempdir(), f"materialized_{name}_{int(time.time()*1000)}.mp4")
        
        st.info(f"💾 Matérialisation de {name} sur disque...")
        
        # Test préalable d'accès aux frames
        try:
            test_frame = clip.get_frame(0)
            if test_frame is None:
                st.warning(f"⚠️ {name}: get_frame retourne None, tentative de récupération...")
                # Essayer de recréer le clip
                if hasattr(clip, 'filename'):
                    st.info(f"🔄 Rechargement depuis {clip.filename}")
                    clip = VideoFileClip(clip.filename)
                else:
                    st.error(f"❌ {name}: Impossible de récupérer le clip")
                    return None
        except Exception as e:
            st.error(f"❌ {name}: Erreur test frame: {str(e)}")
            return None
        
        # Écrire le clip sur disque avec des paramètres ultra-légers
        clip.write_videofile(
            temp_path,
            codec='libx264',
            preset='ultrafast',
            fps=VIDEO_FORMAT['fps'],
            audio=False,
            logger=None,
            verbose=False,
            threads=2,
            ffmpeg_params=['-crf', '23']  # Qualité légèrement réduite pour la vitesse
        )
        
        # Fermer le clip original
        clip.close()
        
        # Vérifier que le fichier existe et a une taille raisonnable
        if not os.path.exists(temp_path):
            st.error(f"❌ {name}: Fichier non créé")
            return None
        
        file_size_mb = os.path.getsize(temp_path) / 1024 / 1024
        if file_size_mb < 0.01:
            st.error(f"❌ {name}: Fichier trop petit ({file_size_mb:.2f} MB)")
            return None
        
        st.success(f"✅ {name} matérialisé: {file_size_mb:.1f} MB")
        
        # Recharger le clip depuis le disque
        materialized = VideoFileClip(temp_path)
        
        # Valider le clip rechargé
        if materialized.duration <= 0:
            st.error(f"❌ {name}: Durée invalide après matérialisation")
            materialized.close()
            os.remove(temp_path)
            return None
        
        # Test final d'accès aux frames
        try:
            test_frame = materialized.get_frame(0)
            if test_frame is None:
                st.error(f"❌ {name}: Frames inaccessibles après matérialisation")
                materialized.close()
                os.remove(temp_path)
                return None
        except Exception as e:
            st.error(f"❌ {name}: Test frame échoué après matérialisation: {str(e)}")
            materialized.close()
            os.remove(temp_path)
            return None
        
        st.success(f"✅ {name} rechargé et validé (durée: {materialized.duration:.1f}s)")
        return materialized
        
    except Exception as e:
        st.error(f"❌ Erreur matérialisation {name}: {str(e)}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None


def safe_concatenate_with_materialization(
    clips: List[VideoFileClip], 
    method: str = "compose"
) -> Optional[VideoFileClip]:
    """
    Concaténation ultra-sécurisée avec matérialisation systématique
    
    Args:
        clips: Liste des clips à concaténer
        method: Méthode de concaténation
    
    Returns:
        VideoFileClip concaténé et matérialisé ou None si échec
    """
    if not clips:
        st.error("❌ Aucun clip à concaténer")
        return None
    
    if len(clips) == 1:
        st.info("📹 Un seul clip, matérialisation directe")
        return materialize_clip(clips[0], "single_clip")
    
    st.header("🔗 Concaténation sécurisée avec matérialisation")
    
    # ÉTAPE 1: Matérialiser TOUS les clips individuellement d'abord
    st.info(f"💾 Matérialisation préalable de {len(clips)} clips...")
    materialized_clips = []
    
    for i, clip in enumerate(clips):
        materialized = materialize_clip(clip, f"clip_{i+1}")
        if materialized:
            materialized_clips.append(materialized)
        else:
            st.warning(f"⚠️ Clip {i+1} ignoré (échec matérialisation)")
    
    if not materialized_clips:
        st.error("❌ Aucun clip n'a pu être matérialisé")
        return None
    
    st.success(f"✅ {len(materialized_clips)}/{len(clips)} clips matérialisés")
    
    # ÉTAPE 2: Concaténer les clips matérialisés
    st.info(f"🔗 Concaténation de {len(materialized_clips)} clips matérialisés...")
    
    try:
        # Essayer la concaténation
        concatenated = concatenate_videoclips(materialized_clips, method=method)
        
        if concatenated is None:
            st.error("❌ concatenate_videoclips a retourné None")
            # Nettoyer
            for clip in materialized_clips:
                clip.close()
            return None
        
        st.success(f"✅ Clips concaténés (durée: {concatenated.duration:.1f}s)")
        
        # ÉTAPE 3: Matérialiser immédiatement le résultat
        st.info("💾 Matérialisation du résultat final...")
        final_materialized = materialize_clip(concatenated, "final_concatenated")
        
        # Nettoyer les clips intermédiaires
        for clip in materialized_clips:
            try:
                clip.close()
                # Supprimer le fichier temporaire si possible
                if hasattr(clip, 'filename') and os.path.exists(clip.filename):
                    if 'materialized_' in clip.filename:
                        os.remove(clip.filename)
            except:
                pass
        
        if concatenated != final_materialized:
            concatenated.close()
        
        return final_materialized
        
    except Exception as e:
        st.error(f"❌ Erreur concaténation: {str(e)}")
        
        # Fallback: essayer de concaténer par paires
        if len(materialized_clips) > 2:
            st.warning("🔄 Tentative de concaténation par paires...")
            
            try:
                # Concaténer deux par deux
                while len(materialized_clips) > 1:
                    new_clips = []
                    
                    for i in range(0, len(materialized_clips), 2):
                        if i + 1 < len(materialized_clips):
                            # Concaténer une paire
                            pair = [materialized_clips[i], materialized_clips[i+1]]
                            st.info(f"🔗 Concaténation paire {i//2 + 1}")
                            
                            pair_concat = concatenate_videoclips(pair, method=method)
                            if pair_concat:
                                # Matérialiser immédiatement
                                pair_materialized = materialize_clip(pair_concat, f"pair_{i//2 + 1}")
                                if pair_materialized:
                                    new_clips.append(pair_materialized)
                                pair_concat.close()
                            
                            # Fermer les clips de la paire
                            pair[0].close()
                            pair[1].close()
                        else:
                            # Clip impair restant
                            new_clips.append(materialized_clips[i])
                    
                    materialized_clips = new_clips
                    
                    if len(materialized_clips) == 1:
                        st.success("✅ Concaténation par paires réussie")
                        return materialized_clips[0]
                
            except Exception as e2:
                st.error(f"❌ Échec concaténation par paires: {str(e2)}")
        
        # Dernier recours: retourner le premier clip
        if materialized_clips:
            st.warning("⚠️ Retour du premier clip seulement")
            for clip in materialized_clips[1:]:
                clip.close()
            return materialized_clips[0]
        
        return None


def create_final_video_ultra_safe(
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
    Version ultra-sécurisée avec matérialisation systématique
    """
    import gc
    
    try:
        st.header("🎬 Assemblage ultra-sécurisé de la vidéo")
        
        if not clips:
            st.error("❌ Aucun clip fourni")
            return False
        
        st.info(f"📊 {len(clips)} clips à assembler")
        
        # Mélanger si demandé
        if smart_shuffle and clips_by_video and len(clips_by_video) > 1:
            # Utiliser la fonction smart_shuffle_clips définie localement
            clips = smart_shuffle_clips(clips_by_video)
            st.info("🔀 Mélange intelligent appliqué")
        elif shuffle:
            random.shuffle(clips)
            st.info("🔀 Clips mélangés aléatoirement")
        
        # Préparation et normalisation
        st.info("🔧 Préparation des clips...")
        prepared_clips = prepare_clips_for_concatenation(clips)
        
        if not prepared_clips:
            st.error("❌ Échec de la préparation des clips")
            return False
        
        # CONCATÉNATION ULTRA-SÉCURISÉE avec matérialisation
        final_video = safe_concatenate_with_materialization(
            prepared_clips, 
            method="compose"
        )
        
        if final_video is None:
            st.error("❌ Échec de l'assemblage des clips")
            return False
        
        # Test de validité finale
        try:
            test_frame = final_video.get_frame(0)
            if test_frame is None:
                st.error("❌ La vidéo finale n'est pas fonctionnelle")
                final_video.close()
                return False
            
            st.success(f"✅ Vidéo assemblée et validée (durée: {final_video.duration:.1f}s)")
            
        except Exception as e:
            st.error(f"❌ Erreur validation vidéo finale: {str(e)}")
            final_video.close()
            return False
        
        # Ajuster la durée si nécessaire
        if output_duration and not (audio_config and audio_config.get('adapt_to_audio')):
            if final_video.duration > output_duration:
                st.info(f"✂️ Ajustement durée: {final_video.duration:.1f}s → {output_duration}s")
                final_video = final_video.subclip(0, output_duration)
                # Matérialiser après la coupe
                final_video = materialize_clip(final_video, "final_trimmed")
                if not final_video:
                    st.error("❌ Échec matérialisation après découpe")
                    return False
        
        # Ajouter le logo si configuré
        if logo_config and logo_config.get('logo_path'):
            st.info("🖼️ Ajout du logo...")
            try:
                from video_extractor import add_logo_overlay
                final_video = add_logo_overlay(final_video, **logo_config)
                # Matérialiser après ajout du logo
                final_video = materialize_clip(final_video, "final_with_logo")
                if not final_video:
                    st.warning("⚠️ Logo non ajouté (échec matérialisation)")
            except Exception as e:
                st.warning(f"⚠️ Erreur ajout logo: {str(e)}")
        
        # Ajouter l'audio si configuré
        if audio_config and audio_config.get('audio_path'):
            st.info("🎵 Ajout de l'audio...")
            try:
                from video_extractor import add_audio_to_video
                final_video = add_audio_to_video(final_video, **audio_config)
            except Exception as e:
                st.warning(f"⚠️ Erreur ajout audio: {str(e)}")
                final_video = final_video.without_audio()
        else:
            final_video = final_video.without_audio()
        
        # Ajouter la tagline si configurée
        if tagline_path and os.path.exists(tagline_path):
            st.info("🏷️ Ajout de la tagline...")
            try:
                from video_extractor import add_tagline
                final_video = add_tagline(final_video, tagline_path)
                # Matérialiser après ajout tagline
                final_video = materialize_clip(final_video, "final_with_tagline")
                if not final_video:
                    st.warning("⚠️ Tagline non ajoutée (échec matérialisation)")
            except Exception as e:
                st.warning(f"⚠️ Erreur ajout tagline: {str(e)}")
        
        # Test final avant encodage
        try:
            test_frame = final_video.get_frame(0)
            if test_frame is None:
                st.error("❌ Vidéo finale non fonctionnelle avant encodage")
                final_video.close()
                return False
            st.success("✅ Vidéo finale validée pour encodage")
        except Exception as e:
            st.error(f"❌ Erreur test final: {str(e)}")
            final_video.close()
            return False
        
        # Encodage final
        st.info("💾 Encodage de la vidéo finale...")
        
        encoding_params = {
            'codec': 'libx264',
            'fps': VIDEO_FORMAT['fps'],
            'preset': 'ultrafast' if IS_RAILWAY else 'fast',
            'threads': 2 if IS_RAILWAY else 4,
            'logger': None,
            'verbose': False,
            'write_logfile': False,
            'bitrate': '4000k' if IS_RAILWAY else '6000k',
        }
        
        if final_video.audio is not None:
            encoding_params['audio_codec'] = 'aac'
            encoding_params['audio_bitrate'] = '128k'
        else:
            encoding_params['audio'] = False
        
        # Progress bar
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        try:
            # Écrire la vidéo finale
            final_video.write_videofile(
                output_path,
                **encoding_params,
                temp_audiofile=output_path.replace('.mp4', '_temp_audio.m4a')
            )
            
            progress_bar.progress(100)
            progress_text.text("✅ Encodage terminé!")
            
            # Vérifier le fichier final
            if os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / 1024 / 1024
                if file_size_mb > 0.1:
                    st.success(f"✅ Vidéo créée avec succès: {file_size_mb:.1f} MB")
                else:
                    st.error(f"❌ Fichier trop petit: {file_size_mb:.2f} MB")
                    return False
            else:
                st.error("❌ Fichier de sortie non créé")
                return False
                
        except Exception as e:
            st.error(f"❌ Erreur encodage final: {str(e)}")
            return False
        
        finally:
            # Nettoyage complet
            if final_video:
                final_video.close()
                # Supprimer le fichier temporaire si c'est un fichier matérialisé
                if hasattr(final_video, 'filename') and 'materialized_' in final_video.filename:
                    try:
                        os.remove(final_video.filename)
                    except:
                        pass
            
            # Nettoyer tous les clips
            for clip in clips:
                if hasattr(clip, 'close'):
                    try:
                        clip.close()
                    except:
                        pass
            
            # Forcer la libération mémoire
            gc.collect()
            st.info("🧹 Mémoire libérée")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erreur fatale: {str(e)}")
        
        # Nettoyage en cas d'erreur
        for clip in clips:
            if hasattr(clip, 'close'):
                try:
                    clip.close()
                except:
                    pass
        
        gc.collect()
        return False
