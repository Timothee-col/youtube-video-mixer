"""
Module de normalisation des clips vidéo
Assure que tous les clips ont exactement les mêmes propriétés avant concaténation
"""
import streamlit as st
import numpy as np
from moviepy.editor import VideoFileClip
from typing import List, Tuple
from constants import VIDEO_FORMAT


def normalize_clip_size(clip: VideoFileClip, target_size: Tuple[int, int] = None) -> VideoFileClip:
    """
    Normalise un clip à la taille cible en préservant le contenu au maximum
    
    Args:
        clip: Le clip à normaliser
        target_size: Taille cible (largeur, hauteur). Par défaut utilise VIDEO_FORMAT
    
    Returns:
        VideoFileClip normalisé
    """
    if target_size is None:
        target_size = (VIDEO_FORMAT['width'], VIDEO_FORMAT['height'])
    
    target_width, target_height = target_size
    target_ratio = target_width / target_height
    
    # Si déjà à la bonne taille, retourner tel quel
    if clip.size == target_size:
        return clip
    
    current_width, current_height = clip.size
    current_ratio = current_width / current_height
    
    st.info(f"📐 Normalisation: {clip.size} → {target_size}")
    
    # Stratégie 1: Si les ratios sont proches, simple resize
    if abs(current_ratio - target_ratio) < 0.1:
        return clip.resize(target_size)
    
    # Stratégie 2: Crop + Resize pour préserver le maximum de contenu
    if current_ratio > target_ratio:
        # Video trop large - on crop horizontalement
        new_width = int(current_height * target_ratio)
        x_start = (current_width - new_width) // 2
        clip = clip.crop(x1=x_start, x2=x_start + new_width, y1=0, y2=current_height)
    else:
        # Video trop haute - on crop verticalement
        new_height = int(current_width / target_ratio)
        y_start = (current_height - new_height) // 2
        clip = clip.crop(x1=0, x2=current_width, y1=y_start, y2=y_start + new_height)
    
    # Resize final à la taille exacte
    return clip.resize(target_size)


def normalize_clips_batch(clips: List[VideoFileClip]) -> List[VideoFileClip]:
    """
    Normalise une liste de clips pour qu'ils aient tous les mêmes propriétés
    
    Args:
        clips: Liste des clips à normaliser
    
    Returns:
        Liste des clips normalisés
    """
    if not clips:
        return []
    
    target_size = (VIDEO_FORMAT['width'], VIDEO_FORMAT['height'])
    target_fps = VIDEO_FORMAT['fps']
    
    normalized_clips = []
    
    st.info(f"🔧 Normalisation de {len(clips)} clips...")
    st.info(f"   Cible: {target_size[0]}x{target_size[1]} @ {target_fps} FPS")
    
    for i, clip in enumerate(clips):
        try:
            # Ignorer les clips None ou invalides
            if clip is None:
                st.warning(f"⚠️ Clip {i+1} est None, ignoré")
                continue
            
            if not hasattr(clip, 'size') or not hasattr(clip, 'fps'):
                st.warning(f"⚠️ Clip {i+1} invalide, ignoré")
                continue
            
            # Info sur le clip original
            st.info(f"📹 Clip {i+1}: {clip.size} @ {clip.fps} FPS")
            
            # Normaliser la taille
            normalized = normalize_clip_size(clip, target_size)
            
            # Normaliser le FPS si différent
            if hasattr(clip, 'fps') and clip.fps != target_fps:
                st.info(f"   🎬 Ajustement FPS: {clip.fps} → {target_fps}")
                normalized = normalized.set_fps(target_fps)
            
            # Retirer l'audio pour éviter les problèmes
            if hasattr(normalized, 'audio') and normalized.audio is not None:
                normalized = normalized.without_audio()
                st.info(f"   🔇 Audio retiré")
            
            # Vérification finale
            if normalized.size != target_size:
                st.error(f"❌ Échec normalisation clip {i+1}: taille {normalized.size}")
                continue
            
            # Test d'accès aux frames
            try:
                test_frame = normalized.get_frame(0)
                if test_frame is None:
                    st.error(f"❌ Clip {i+1} normalisé retourne None")
                    continue
                
                normalized_clips.append(normalized)
                st.success(f"✅ Clip {i+1} normalisé avec succès")
                
            except Exception as e:
                st.error(f"❌ Clip {i+1} non fonctionnel après normalisation: {str(e)}")
                continue
                
        except Exception as e:
            st.error(f"❌ Erreur normalisation clip {i+1}: {str(e)}")
            continue
    
    st.info(f"✅ {len(normalized_clips)}/{len(clips)} clips normalisés avec succès")
    
    return normalized_clips


def verify_clips_compatibility(clips: List[VideoFileClip]) -> bool:
    """
    Vérifie que tous les clips sont compatibles pour la concaténation
    
    Args:
        clips: Liste des clips à vérifier
    
    Returns:
        True si tous les clips sont compatibles
    """
    if not clips:
        st.error("❌ Aucun clip à vérifier")
        return False
    
    # Récupérer les propriétés du premier clip comme référence
    first_clip = clips[0]
    ref_size = first_clip.size
    ref_fps = getattr(first_clip, 'fps', 30)
    
    st.info(f"🔍 Vérification de compatibilité ({len(clips)} clips)")
    st.info(f"   Référence: {ref_size} @ {ref_fps} FPS")
    
    all_compatible = True
    
    for i, clip in enumerate(clips):
        issues = []
        
        # Vérifier la taille
        if clip.size != ref_size:
            issues.append(f"Taille: {clip.size} ≠ {ref_size}")
            all_compatible = False
        
        # Vérifier le FPS
        clip_fps = getattr(clip, 'fps', 30)
        if abs(clip_fps - ref_fps) > 1:  # Tolérance de 1 FPS
            issues.append(f"FPS: {clip_fps} ≠ {ref_fps}")
            all_compatible = False
        
        # Vérifier l'accès aux frames
        try:
            frame = clip.get_frame(0)
            if frame is None:
                issues.append("get_frame retourne None")
                all_compatible = False
        except Exception as e:
            issues.append(f"Erreur get_frame: {str(e)}")
            all_compatible = False
        
        # Afficher le résultat
        if issues:
            st.warning(f"⚠️ Clip {i+1} incompatible: {', '.join(issues)}")
        else:
            st.success(f"✅ Clip {i+1} compatible")
    
    if all_compatible:
        st.success("✅ Tous les clips sont compatibles pour la concaténation")
    else:
        st.warning("⚠️ Des clips nécessitent une normalisation")
    
    return all_compatible


def prepare_clips_for_concatenation(clips: List[VideoFileClip]) -> List[VideoFileClip]:
    """
    Prépare et normalise les clips pour une concaténation sans erreur
    
    Args:
        clips: Liste des clips à préparer
    
    Returns:
        Liste des clips prêts pour la concaténation
    """
    st.header("🎬 Préparation des clips pour concaténation")
    
    # Étape 1: Vérifier la compatibilité
    if verify_clips_compatibility(clips):
        st.info("✅ Clips déjà compatibles, pas de normalisation nécessaire")
        return clips
    
    # Étape 2: Normaliser tous les clips
    st.info("🔧 Normalisation nécessaire...")
    normalized = normalize_clips_batch(clips)
    
    # Étape 3: Vérifier à nouveau
    if verify_clips_compatibility(normalized):
        st.success("✅ Clips normalisés et prêts pour la concaténation")
        return normalized
    else:
        st.error("❌ Échec de la normalisation")
        return []
