"""
Module de détection et suppression de texte
"""
import cv2
import numpy as np
import urllib.request
import os
import streamlit as st
from typing import List, Dict, Optional, Tuple
from constants import EAST_MODEL_URL, EAST_DNN_PARAMS, DETECTION_PARAMS, INPAINT_PARAMS

def download_east_model(temp_dir: str) -> Optional[str]:
    """
    Télécharge le modèle EAST pour la détection de texte
    
    Args:
        temp_dir: Répertoire temporaire
    
    Returns:
        str: Chemin du modèle ou None si erreur
    """
    model_path = os.path.join(temp_dir, "frozen_east_text_detection.pb")
    
    if not os.path.exists(model_path):
        with st.spinner("Téléchargement du modèle de détection de texte (première fois seulement)..."):
            try:
                urllib.request.urlretrieve(EAST_MODEL_URL, model_path)
                st.success("✅ Modèle de détection de texte téléchargé!")
            except Exception as e:
                st.error(f"Erreur lors du téléchargement du modèle: {str(e)}")
                return None
    
    return model_path

def load_text_detection_model(model_path: str) -> Optional[cv2.dnn_Net]:
    """
    Charge le modèle de détection de texte
    
    Args:
        model_path: Chemin du modèle
    
    Returns:
        cv2.dnn_Net: Modèle chargé ou None si erreur
    """
    try:
        net = cv2.dnn.readNet(model_path)
        return net
    except Exception as e:
        st.error(f"Erreur lors du chargement du modèle: {str(e)}")
        return None

def detect_text_in_frame(frame: np.ndarray, net: Optional[cv2.dnn_Net] = None, 
                        focus_on_subtitles: bool = True) -> float:
    """
    Détecte la présence de texte dans une frame
    
    Args:
        frame: Frame à analyser
        net: Modèle EAST
        focus_on_subtitles: Se concentrer sur la zone des sous-titres
    
    Returns:
        float: Score de 0 à 1 (1 = beaucoup de texte)
    """
    if net is None:
        return 0.0
    
    try:
        orig_h, orig_w = frame.shape[:2]
        
        # Détection rapide des sous-titres
        if focus_on_subtitles:
            subtitle_zone = frame[int(orig_h * DETECTION_PARAMS['subtitle_zone_ratio']):, :]
            gray_zone = cv2.cvtColor(subtitle_zone, cv2.COLOR_BGR2GRAY)
            
            # Seuillage pour détecter le texte blanc
            _, white_text = cv2.threshold(gray_zone, 200, 255, cv2.THRESH_BINARY)
            white_pixels = np.sum(white_text > 0)
            
            # Si beaucoup de pixels blancs en bas = probablement des sous-titres
            subtitle_ratio = white_pixels / (subtitle_zone.shape[0] * subtitle_zone.shape[1])
            if subtitle_ratio > 0.01:  # Plus de 1% de pixels blancs
                return 0.8
        
        # EAST pour la détection générale
        scores, geometry = _run_east_detection(frame, net)
        
        if scores is None:
            return 0.0
        
        # Analyser les scores
        confidences = []
        bottom_text_count = 0
        numRows, numCols = scores.shape[2:4]
        
        for y in range(numRows):
            scoresData = scores[0, 0, y]
            
            for x in range(numCols):
                if scoresData[x] < DETECTION_PARAMS['text_detection_threshold']:
                    continue
                
                confidences.append(scoresData[x])
                
                # Vérifier si le texte est en bas
                if y > numRows * 0.7:
                    bottom_text_count += 1
        
        # Calculer le score final
        if len(confidences) > 0:
            avg_confidence = np.mean(confidences)
            num_detections = len(confidences)
            
            text_score = min((num_detections / 20) * avg_confidence, 1.0)
            
            # Bonus si le texte est en bas
            if bottom_text_count > 2:
                text_score = min(text_score * 1.5, 1.0)
            
            return text_score
        
        return 0.0
        
    except Exception:
        return 0.0

def detect_text_regions(frame: np.ndarray, net: Optional[cv2.dnn_Net] = None) -> List[Dict]:
    """
    Détecte les régions de texte et retourne leurs coordonnées
    
    Args:
        frame: Frame à analyser
        net: Modèle EAST
    
    Returns:
        List[Dict]: Régions de texte détectées
    """
    if net is None:
        return []
    
    try:
        orig_h, orig_w = frame.shape[:2]
        
        scores, geometry = _run_east_detection(frame, net)
        
        if scores is None:
            return []
        
        # Décoder les prédictions
        rects = _decode_predictions(scores, geometry, orig_w, orig_h)
        
        return rects
        
    except Exception:
        return []

def _run_east_detection(frame: np.ndarray, net: cv2.dnn_Net) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Exécute la détection EAST sur une frame
    
    Args:
        frame: Frame à analyser
        net: Modèle EAST
    
    Returns:
        Tuple: (scores, geometry) ou (None, None) si erreur
    """
    try:
        new_h, new_w = EAST_DNN_PARAMS['blob_size']
        
        # Redimensionner l'image
        resized = cv2.resize(frame, (new_w, new_h))
        
        # Créer le blob
        blob = cv2.dnn.blobFromImage(
            resized, 1.0, (new_w, new_h),
            EAST_DNN_PARAMS['mean_values'], 
            swapRB=EAST_DNN_PARAMS['swap_rb'], 
            crop=EAST_DNN_PARAMS['crop']
        )
        
        # Passer dans le réseau
        net.setInput(blob)
        (scores, geometry) = net.forward([
            "feature_fusion/Conv_7/Sigmoid",
            "feature_fusion/concat_3"
        ])
        
        return scores, geometry
        
    except Exception:
        return None, None

def _decode_predictions(scores: np.ndarray, geometry: np.ndarray, 
                       orig_w: int, orig_h: int) -> List[Dict]:
    """
    Décode les prédictions EAST en régions
    
    Args:
        scores: Scores de détection
        geometry: Géométrie des détections
        orig_w: Largeur originale
        orig_h: Hauteur originale
    
    Returns:
        List[Dict]: Régions décodées
    """
    new_h, new_w = EAST_DNN_PARAMS['blob_size']
    rW = orig_w / float(new_w)
    rH = orig_h / float(new_h)
    
    numRows, numCols = scores.shape[2:4]
    rects = []
    
    for y in range(numRows):
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]
        
        for x in range(numCols):
            if scoresData[x] < DETECTION_PARAMS['text_detection_threshold']:
                continue
            
            # Calculer les coordonnées
            offsetX, offsetY = (x * 4.0, y * 4.0)
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)
            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]
            
            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)
            
            # Ajuster aux dimensions originales
            startX = int(startX * rW)
            startY = int(startY * rH)
            endX = int(endX * rW)
            endY = int(endY * rH)
            
            rects.append({
                'x': max(0, startX),
                'y': max(0, startY),
                'width': min(orig_w - startX, endX - startX),
                'height': min(orig_h - startY, endY - startY),
                'confidence': float(scoresData[x])
            })
    
    return rects

def remove_text_with_crop(frame: np.ndarray, text_regions: List[Dict], 
                         target_aspect_ratio: float = 9/16) -> np.ndarray:
    """
    Recadre l'image pour exclure les zones de texte
    
    Args:
        frame: Frame à recadrer
        text_regions: Régions de texte détectées
        target_aspect_ratio: Ratio cible (9:16 par défaut)
    
    Returns:
        np.ndarray: Frame recadrée
    """
    h, w = frame.shape[:2]
    
    if not text_regions:
        return frame
    
    # Trouver les limites du texte
    min_y = h
    max_y = 0
    
    for region in text_regions:
        y, height = region['y'], region['height']
        min_y = min(min_y, y)
        max_y = max(max_y, y + height)
    
    # Stratégie de crop selon la position du texte
    if max_y > h * 0.7:  # Texte en bas
        new_h = int(min_y * 0.9)
        crop_y_start = 0
        crop_y_end = new_h
    elif min_y < h * 0.3:  # Texte en haut
        crop_y_start = int(max_y * 1.1)
        crop_y_end = h
        new_h = crop_y_end - crop_y_start
    else:  # Texte au milieu
        crop_y_start = 0
        crop_y_end = min_y
        new_h = crop_y_end - crop_y_start
    
    # Calculer la largeur pour le ratio
    new_w = int(new_h * target_aspect_ratio)
    
    # Centrer horizontalement
    if new_w > w:
        new_w = w
        new_h = int(new_w / target_aspect_ratio)
    
    crop_x_start = (w - new_w) // 2
    crop_x_end = crop_x_start + new_w
    
    # Vérifier la validité
    if crop_y_end > crop_y_start and crop_x_end > crop_x_start:
        cropped = frame[crop_y_start:crop_y_end, crop_x_start:crop_x_end]
        # Redimensionner au format final
        if cropped.shape[0] != 1920 or cropped.shape[1] != 1080:
            cropped = cv2.resize(cropped, (1080, 1920))
        return cropped
    
    return frame

def remove_text_with_inpainting(frame: np.ndarray, text_regions: List[Dict]) -> np.ndarray:
    """
    Utilise l'inpainting pour enlever le texte
    
    Args:
        frame: Frame à traiter
        text_regions: Régions de texte détectées
    
    Returns:
        np.ndarray: Frame avec texte supprimé
    """
    h, w = frame.shape[:2]
    
    # Créer un masque pour les régions de texte
    mask = np.zeros((h, w), dtype=np.uint8)
    
    padding = INPAINT_PARAMS['padding']
    
    for region in text_regions:
        x, y = region['x'], region['y']
        width, height = region['width'], region['height']
        
        # Agrandir légèrement la zone
        x = max(0, x - padding)
        y = max(0, y - padding)
        width = min(w - x, width + 2 * padding)
        height = min(h - y, height + 2 * padding)
        
        mask[y:y+height, x:x+width] = 255
    
    # Appliquer l'inpainting
    if np.any(mask > 0):
        result = cv2.inpaint(
            frame, mask, 
            inpaintRadius=INPAINT_PARAMS['radius'], 
            flags=cv2.INPAINT_TELEA
        )
        return result
    
    return frame

def calculate_text_penalty(text_score: float) -> float:
    """
    Calcule la pénalité à appliquer en fonction du score de texte
    
    Args:
        text_score: Score de texte (0 à 1)
    
    Returns:
        float: Pénalité à appliquer (0 à 1)
    """
    if text_score > 0.3:
        return DETECTION_PARAMS['text_penalty_high']
    elif text_score > 0.2:
        return DETECTION_PARAMS['text_penalty_medium']
    else:
        return 1.0  # Pas de pénalité