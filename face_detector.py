"""
Module de détection faciale avec fallback si face_recognition n'est pas disponible
"""
import cv2
import numpy as np
import streamlit as st
from typing import Optional, List, Dict, Tuple

# Tentative d'import de face_recognition
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    st.info("✅ Module face_recognition disponible")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    st.warning("⚠️ Module face_recognition non disponible - fonctionnement en mode basique")

def extract_face_encoding_from_image(image_path: str) -> Optional[np.ndarray]:
    """
    Extrait l'encoding facial d'une image de référence
    
    Args:
        image_path: Chemin vers l'image
        
    Returns:
        Encoding facial ou None si pas de visage détecté
    """
    if not FACE_RECOGNITION_AVAILABLE:
        st.warning("⚠️ Reconnaissance faciale désactivée (face_recognition non installé)")
        return None
    
    try:
        # Charger l'image
        image = face_recognition.load_image_file(image_path)
        
        # Extraire les encodings
        face_encodings = face_recognition.face_encodings(image)
        
        if face_encodings:
            st.success(f"✅ Visage détecté et encodé")
            return face_encodings[0]
        else:
            st.warning("⚠️ Aucun visage détecté dans l'image de référence")
            return None
            
    except Exception as e:
        st.error(f"❌ Erreur lors de l'extraction du visage: {str(e)}")
        return None

def detect_faces_in_frame(frame: np.ndarray, target_encoding: Optional[np.ndarray] = None, threshold: float = 0.6) -> Tuple[bool, List[Dict]]:
    """
    Détecte les visages dans une frame
    
    Args:
        frame: Frame à analyser
        target_encoding: Encoding du visage cible (optionnel)
        threshold: Seuil de similarité
        
    Returns:
        (has_target_face, face_locations)
    """
    if not FACE_RECOGNITION_AVAILABLE:
        # Fallback avec OpenCV Haar Cascades
        return detect_faces_opencv(frame)
    
    try:
        # Redimensionner pour accélérer
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Détecter les visages
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        
        if not face_locations:
            return False, []
        
        # Si pas de cible, retourner juste la présence de visages
        if target_encoding is None:
            face_dicts = []
            for (top, right, bottom, left) in face_locations:
                face_dicts.append({
                    'x': left * 4,
                    'y': top * 4,
                    'width': (right - left) * 4,
                    'height': (bottom - top) * 4
                })
            return True, face_dicts
        
        # Comparer avec la cible
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        has_target = False
        face_dicts = []
        
        for encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            # Calculer la distance
            distance = face_recognition.face_distance([target_encoding], encoding)[0]
            
            face_dict = {
                'x': left * 4,
                'y': top * 4,
                'width': (right - left) * 4,
                'height': (bottom - top) * 4,
                'distance': distance
            }
            face_dicts.append(face_dict)
            
            if distance < threshold:
                has_target = True
                face_dict['is_target'] = True
        
        return has_target, face_dicts
        
    except Exception as e:
        st.warning(f"⚠️ Erreur détection: {str(e)}")
        return False, []

def detect_faces_opencv(frame: np.ndarray) -> Tuple[bool, List[Dict]]:
    """
    Fallback: Détection de visages avec OpenCV Haar Cascades
    
    Args:
        frame: Frame à analyser
        
    Returns:
        (has_faces, face_locations)
    """
    try:
        # Charger le classifier Haar Cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Convertir en niveaux de gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Détecter les visages
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        face_dicts = []
        for (x, y, w, h) in faces:
            face_dicts.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h
            })
        
        return len(faces) > 0, face_dicts
        
    except Exception as e:
        return False, []

def get_face_regions_for_crop(frame: np.ndarray, target_encoding: Optional[np.ndarray] = None, threshold: float = 0.6) -> List[Dict]:
    """
    Obtient les régions de visages pour le crop intelligent
    
    Args:
        frame: Frame à analyser
        target_encoding: Encoding du visage cible
        threshold: Seuil de similarité
        
    Returns:
        Liste des régions de visages
    """
    _, face_regions = detect_faces_in_frame(frame, target_encoding, threshold)
    return face_regions

# Fonction de test pour vérifier la disponibilité
def check_face_recognition_status():
    """
    Vérifie et affiche le statut du module face_recognition
    """
    if FACE_RECOGNITION_AVAILABLE:
        return "✅ Reconnaissance faciale complète disponible"
    else:
        return "⚠️ Mode basique (OpenCV) - Installez cmake et face-recognition pour la reconnaissance complète"
