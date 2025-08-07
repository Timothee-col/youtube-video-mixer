"""
Module d'analyse des segments vidéo
"""
import cv2
import numpy as np
import streamlit as st
import random
from typing import List, Dict, Optional, Tuple
from moviepy.editor import VideoFileClip
from constants import ANALYSIS_MODES, SCORING_WEIGHTS, DETECTION_PARAMS
from face_detector import detect_faces_in_frame, calculate_face_score, detect_faces_haar_cascade
from text_detector import detect_text_in_frame, calculate_text_penalty

def calculate_visual_interest_score(frame: np.ndarray) -> float:
    """
    Calcule le score d'intérêt visuel d'une frame
    
    Args:
        frame: Frame à analyser
    
    Returns:
        float: Score d'intérêt visuel
    """
    # Convertir en HSV pour une meilleure analyse des couleurs
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Diversité des couleurs
    hist_hue = cv2.calcHist([hsv], [0], None, [180], [0, 180])
    color_diversity = np.std(hist_hue)
    
    # Variation de luminosité
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness_std = np.std(gray)
    
    # Détection des contours pour la complexité visuelle
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    # Détection du flou de mouvement (plus c'est net, mieux c'est)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    
    # Combiner les scores
    score = (
        color_diversity * 0.2 + 
        brightness_std * 0.2 + 
        edge_density * 10000 * 0.3 + 
        sharpness * 0.3
    )
    
    return score

def calculate_motion_score(frame: np.ndarray, prev_frame: Optional[np.ndarray]) -> float:
    """
    Calcule le score de mouvement entre deux frames
    
    Args:
        frame: Frame actuelle
        prev_frame: Frame précédente
    
    Returns:
        float: Score de mouvement
    """
    if prev_frame is None:
        return 0.0
    
    try:
        # Calculer la différence absolue
        diff = cv2.absdiff(frame, prev_frame)
        motion_score = np.mean(diff) * 10
        return motion_score
    except:
        return 0.0

def analyze_video_segments_with_face(
    video_path: str,
    target_face_encoding: Optional[np.ndarray] = None,
    segment_duration: float = 5,
    min_clip_duration: float = 3,
    max_clip_duration: float = 10,
    video_index: int = 0,
    analysis_mode: str = "🎯 Précis (3-5 min)",
    avoid_text: bool = False,
    text_net: Optional[cv2.dnn_Net] = None,
    remove_text_method: Optional[str] = None,
    exclude_first_seconds: float = 0,
    face_threshold: float = 0.4
) -> List[Dict]:
    """
    Analyse une vidéo et retourne les meilleurs segments
    
    Args:
        video_path: Chemin de la vidéo
        target_face_encoding: Encoding du visage cible
        segment_duration: Durée d'un segment d'analyse
        min_clip_duration: Durée minimale d'un clip
        max_clip_duration: Durée maximale d'un clip
        video_index: Index de la vidéo
        analysis_mode: Mode d'analyse choisi
        avoid_text: Si True, évite les segments avec du texte
        text_net: Modèle de détection de texte
        remove_text_method: Méthode de suppression de texte
    
    Returns:
        List[Dict]: Liste des meilleurs segments
    """
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    # Vérifier la durée minimale
    if duration < min_clip_duration:
        cap.release()
        return []
    
    # Paramètres selon le mode d'analyse
    mode_params = ANALYSIS_MODES.get(analysis_mode, ANALYSIS_MODES['🎯 Précis (3-5 min)'])
    analysis_segment_duration = mode_params['segment_duration']
    frames_per_segment = mode_params['frames_per_segment']
    max_segments = mode_params['max_segments']
    face_model = mode_params['face_model']
    upsample = mode_params['upsample']
    
    # Calculer le nombre de segments en tenant compte des exclusions
    available_duration = duration - exclude_first_seconds
    num_segments = min(max_segments, int((available_duration - min_clip_duration) / analysis_segment_duration))
    segment_scores = []
    
    # Fallback pour la détection de visages
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Interface de progression
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    prev_frame = None
    
    for i in range(num_segments):
        progress_text.text(f"Analyse {analysis_mode.split()[0]} - Segment {i+1}/{num_segments}")
        progress_bar.progress((i + 1) / num_segments)
        
        # Calculer le temps de début en tenant compte de l'exclusion
        start_time = exclude_first_seconds + (i * analysis_segment_duration)
        
        # Vérifier qu'on ne dépasse pas la durée
        if start_time + min_clip_duration > duration:
            break
        
        scores_in_segment = []
        has_target_face = False
        face_locations_in_segment = []
        
        # Analyser plusieurs frames dans le segment
        for j in range(frames_per_segment):
            frame_time = start_time + (j * analysis_segment_duration / frames_per_segment)
            frame_pos = int(frame_time * fps)
            
            if frame_pos >= total_frames:
                break
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Score d'intérêt visuel
            visual_score = calculate_visual_interest_score(frame)
            
            # Détection de visages
            face_score = 0
            if target_face_encoding is not None:
                # Détection avec face_recognition
                faces_data = detect_faces_in_frame(
                    frame, target_face_encoding, 
                    model=face_model, upsample=upsample,
                    similarity_threshold=face_threshold
                )
                
                if faces_data:
                    face_score = calculate_face_score(faces_data, has_target=True)
                    # Vérifier si le visage cible est présent
                    for face in faces_data:
                        if face['is_target']:
                            has_target_face = True
                            face_locations_in_segment.extend(faces_data)
                            break
            else:
                # Détection simple avec Haar Cascade
                faces_data = detect_faces_haar_cascade(frame)
                face_score = len(faces_data) * 200
            
            # Score de mouvement
            motion_score = calculate_motion_score(frame, prev_frame)
            prev_frame = frame.copy()
            
            # Détection de texte et pénalité
            text_penalty = 1.0
            if avoid_text and text_net is not None and remove_text_method is None:
                if analysis_mode != "⚡ Rapide (1-2 min)":  # Skip pour le mode rapide
                    text_score = detect_text_in_frame(frame, text_net, focus_on_subtitles=True)
                    text_penalty = calculate_text_penalty(text_score)
            
            # Score total pour cette frame
            total_score = (
                visual_score * SCORING_WEIGHTS['visual_interest'] +
                face_score * SCORING_WEIGHTS['face_detection'] +
                motion_score * SCORING_WEIGHTS['motion']
            ) * text_penalty
            
            scores_in_segment.append(total_score)
        
        # Calculer le score moyen du segment
        if scores_in_segment:
            avg_score = np.mean(scores_in_segment)
            
            # Boost si le visage cible est détecté
            if has_target_face:
                avg_score *= SCORING_WEIGHTS['face_boost']
            
            segment_scores.append({
                'start_time': start_time,
                'score': avg_score,
                'has_target_face': has_target_face,
                'video_index': video_index,
                'face_locations': face_locations_in_segment
            })
    
    cap.release()
    progress_bar.empty()
    progress_text.empty()
    
    # Trier par score et créer les clips
    segment_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # Prioriser les segments avec le visage cible
    if target_face_encoding is not None:
        segments_with_face = [s for s in segment_scores if s['has_target_face']]
        segments_without_face = [s for s in segment_scores if not s['has_target_face']]
        segment_scores = segments_with_face + segments_without_face
    
    # Créer les clips finaux avec plus de diversité
    min_distance = 10.0 if 'force_diversity' in locals() and force_diversity else 5.0
    clips = create_clips_from_segments(
        segment_scores, duration, 
        min_clip_duration, max_clip_duration,
        min_distance_between_clips=min_distance
    )
    
    return clips

def create_clips_from_segments(
    segment_scores: List[Dict],
    video_duration: float,
    min_clip_duration: float,
    max_clip_duration: float,
    min_distance_between_clips: float = 5.0  # Nouvelle option
) -> List[Dict]:
    """
    Crée des clips à partir des segments analysés
    
    Args:
        segment_scores: Segments triés par score
        video_duration: Durée totale de la vidéo
        min_clip_duration: Durée minimale d'un clip
        max_clip_duration: Durée maximale d'un clip
    
    Returns:
        List[Dict]: Liste des clips créés
    """
    clips = []
    used_times = set()
    
    for segment in segment_scores:
        start = segment['start_time']
        
        # Vérifier la distance minimale avec les clips existants
        too_close = False
        for used_time in used_times:
            if abs(start - used_time) < min_distance_between_clips:
                too_close = True
                break
        
        if too_close:
            continue
        
        # Vérifier qu'on a assez de temps restant
        remaining_duration = video_duration - start
        if remaining_duration < min_clip_duration:
            continue
        
        # Déterminer la durée du clip
        max_possible_duration = min(max_clip_duration, remaining_duration)
        clip_duration = random.uniform(min_clip_duration, max_possible_duration)
        
        end_time = start + clip_duration
        
        # Vérifications finales
        if end_time > video_duration:
            end_time = video_duration
            clip_duration = end_time - start
        
        if clip_duration >= min_clip_duration and start < video_duration:
            clips.append({
                'start': start,
                'end': end_time,
                'duration': clip_duration,
                'score': segment['score'],
                'has_target_face': segment.get('has_target_face', False),
                'video_index': segment.get('video_index', 0),
                'face_locations': segment.get('face_locations', [])
            })
            used_times.add(start)
    
    return clips

def merge_adjacent_high_score_segments(
    segments: List[Dict],
    threshold_score: float,
    max_gap: float = 2.0
) -> List[Dict]:
    """
    Fusionne les segments adjacents avec des scores élevés
    
    Args:
        segments: Liste des segments
        threshold_score: Score minimum pour la fusion
        max_gap: Écart maximum entre segments pour fusion
    
    Returns:
        List[Dict]: Segments fusionnés
    """
    if not segments:
        return segments
    
    # Trier par temps de début
    sorted_segments = sorted(segments, key=lambda x: x['start_time'])
    merged = []
    
    current = sorted_segments[0].copy()
    
    for next_segment in sorted_segments[1:]:
        # Vérifier si on peut fusionner
        gap = next_segment['start_time'] - (current.get('end_time', current['start_time'] + 1))
        
        if (gap <= max_gap and 
            current['score'] >= threshold_score and 
            next_segment['score'] >= threshold_score):
            # Fusionner
            current['end_time'] = next_segment.get('end_time', next_segment['start_time'] + 1)
            current['score'] = max(current['score'], next_segment['score'])
            current['has_target_face'] = current.get('has_target_face', False) or next_segment.get('has_target_face', False)
        else:
            # Ajouter le segment actuel et passer au suivant
            merged.append(current)
            current = next_segment.copy()
    
    # Ajouter le dernier segment
    merged.append(current)
    
    return merged