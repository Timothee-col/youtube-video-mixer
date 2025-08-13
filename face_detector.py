"""
Module de détection et reconnaissance faciale
"""
import streamlit as st
import numpy as np
from typing import List, Dict, Optional, Tuple

# Import conditionnel de cv2
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    st.warning("⚠️ OpenCV non disponible")

# Import conditionnel de face_recognition
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    face_recognition = None
    st.warning("⚠️ face_recognition non disponible")

from constants import DETECTION_PARAMS

def extract_face_encoding_from_image(image_path: str) -> Optional[np.ndarray]:
    """
    Extrait l'encoding facial d'une image de référence
    
    Args:
        image_path: Chemin de l'image
    
    Returns:
        np.ndarray: Encoding facial ou None si pas de visage
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return None
        
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return None
        
        # Si plusieurs visages, prendre le plus grand
        if len(face_locations) > 1:
            largest_face = max(face_locations, key=lambda loc: (loc[2]-loc[0]) * (loc[1]-loc[3]))
            face_locations = [largest_face]
        
        encodings = face_recognition.face_encodings(image, face_locations)
        if encodings:
            return encodings[0]
        return None
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'image de référence: {str(e)}")
        return None

def detect_faces_in_frame(frame: np.ndarray, target_encoding: Optional[np.ndarray] = None, 
                         model: str = "hog", upsample: int = 1,
                         similarity_threshold: float = 0.4) -> List[Dict]:
    """
    Détecte les visages dans une frame
    
    Args:
        frame: Frame à analyser
        target_encoding: Encoding du visage cible (optionnel)
        model: Modèle de détection ("hog" ou "cnn")
        upsample: Nombre d'upsampling
        similarity_threshold: Seuil de similarité
    
    Returns:
        List[Dict]: Liste des visages détectés avec leurs scores
    """
    faces_data = []
    
    if not FACE_RECOGNITION_AVAILABLE or not CV2_AVAILABLE:
        # Fallback avec Haar Cascade
        return detect_faces_haar_cascade(frame)
    
    try:
        # Convertir BGR en RGB pour face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Détecter les visages
        face_locations = face_recognition.face_locations(
            rgb_frame, 
            model=model, 
            number_of_times_to_upsample=upsample
        )
        
        if not face_locations:
            return faces_data
        
        # Obtenir les encodings
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        frame_height, frame_width = frame.shape[:2]
        
        for face_location, encoding in zip(face_locations, face_encodings):
            top, right, bottom, left = face_location
            
            face_data = {
                'location': face_location,
                'x': left,
                'y': top,
                'width': right - left,
                'height': bottom - top,
                'encoding': encoding,
                'is_target': False,
                'similarity_score': 0.0,
                'position_score': 1.0,
                'size_score': 0.0
            }
            
            # Calculer la taille relative du visage
            face_area = face_data['width'] * face_data['height']
            frame_area = frame_width * frame_height
            face_data['size_score'] = (face_area / frame_area) * 1000
            
            # Calculer le score de position (pénaliser les visages trop bas)
            vertical_position = top / frame_height
            if vertical_position > 0.7:  # Visage dans le tiers inférieur
                face_data['position_score'] = 0.3
            elif vertical_position > 0.5:  # Visage dans la moitié inférieure
                face_data['position_score'] = 0.7
            
            # Si on a un visage cible, calculer la similarité
            if target_encoding is not None:
                distance = face_recognition.face_distance([target_encoding], encoding)[0]
                face_data['similarity_score'] = 1.0 - distance
                
                if distance < similarity_threshold:
                    face_data['is_target'] = True
            
            faces_data.append(face_data)
            
    except Exception as e:
        # Ignorer les erreurs silencieusement pour ne pas interrompre l'analyse
        pass
    
    return faces_data

def calculate_face_score(faces_data: List[Dict], has_target: bool = False) -> float:
    """
    Calcule un score global pour les visages détectés
    
    Args:
        faces_data: Liste des visages détectés
        has_target: Si on recherche un visage spécifique
    
    Returns:
        float: Score calculé
    """
    if not faces_data:
        return 0.0
    
    total_score = 0.0
    
    for face in faces_data:
        # Score de base : taille * position
        face_score = face.get('size_score', 0) * face.get('position_score', 1)
        
        # Bonus si c'est le visage cible
        if has_target and face.get('is_target', False):
            face_score *= 3.0  # Triple le score pour le visage cible
        
        total_score += face_score
    
    # Bonus si plusieurs visages (scène animée)
    if len(faces_data) > 1:
        total_score *= 1.2
    
    return total_score

def get_face_regions_for_crop(frame: np.ndarray, target_encoding: Optional[np.ndarray] = None,
                              face_threshold: float = 0.4) -> List[Dict]:
    """
    Obtient les régions de visages pour le crop intelligent
    
    Args:
        frame: Frame à analyser
        target_encoding: Encoding du visage cible (optionnel)
        face_threshold: Seuil de similarité
    
    Returns:
        List[Dict]: Régions des visages pour le crop
    """
    faces_data = detect_faces_in_frame(frame, target_encoding, model="hog",
                                      similarity_threshold=face_threshold)
    
    # Si on a un visage cible, prioriser ses régions
    if target_encoding is not None:
        target_faces = [f for f in faces_data if f.get('is_target', False)]
        if target_faces:
            return target_faces
    
    # Sinon retourner tous les visages
    return faces_data

def detect_faces_haar_cascade(frame: np.ndarray) -> List[Dict]:
    """
    Détection rapide de visages avec Haar Cascade (fallback)
    
    Args:
        frame: Frame à analyser
    
    Returns:
        List[Dict]: Liste des visages détectés
    """
    if not CV2_AVAILABLE:
        return []
        
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    faces_data = []
    for (x, y, w, h) in faces:
        faces_data.append({
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'is_target': False,
            'size_score': (w * h) / (frame.shape[0] * frame.shape[1]) * 1000
        })
    
    return faces_data

def is_face_in_good_position(face_data: Dict, frame_height: int) -> bool:
    """
    Vérifie si un visage est dans une bonne position (pas trop bas)
    
    Args:
        face_data: Données du visage
        frame_height: Hauteur de la frame
    
    Returns:
        bool: True si la position est bonne
    """
    vertical_position = face_data['y'] / frame_height
    return vertical_position < 0.7  # Pas dans le tiers inférieur

# Fonction de compatibilité pour l'ancienne API
def check_face_recognition_status():
    """
    Vérifie et affiche le statut du module face_recognition
    """
    if FACE_RECOGNITION_AVAILABLE:
        return "✅ Reconnaissance faciale complète disponible"
    else:
        return "⚠️ Mode basique (OpenCV) - Installez cmake et face-recognition pour la reconnaissance complète"
