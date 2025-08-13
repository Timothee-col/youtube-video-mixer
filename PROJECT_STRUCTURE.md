# 📁 Structure du Projet

## Fichiers Principaux

### 🎬 Application
- **`upload_video_mixer.py`** - Interface Streamlit principale
- **`constants.py`** - Configuration et paramètres globaux
- **`requirements.txt`** - Dépendances Python

### 🎯 Modules de Traitement Vidéo

#### 📤 **`video_extractor.py`** - EXTRACTION des clips
Module responsable de l'extraction des meilleurs moments depuis les vidéos sources.
- `extract_best_clips_with_face()` - Extraction avec reconnaissance faciale
- `resize_and_center_vertical()` - Conversion au format 9:16
- `add_logo_overlay()` - Ajout d'un logo en overlay
- `add_audio_to_video()` - Ajout d'une piste audio
- `add_tagline()` - Ajout d'une vidéo tagline

#### 🔗 **`video_assembler.py`** - ASSEMBLAGE final
Module responsable de l'assemblage des clips en vidéo finale avec matérialisation.
- `create_final_video_ultra_safe()` - Création de la vidéo finale
- `materialize_clip()` - Matérialisation sur disque (résout les bugs MoviePy)
- `safe_concatenate_with_materialization()` - Concaténation robuste
- `smart_shuffle_clips()` - Mélange intelligent des clips

#### 🔧 **`video_normalizer.py`** - NORMALISATION
- Normalise tous les clips au même format (1080x1920, 30 FPS)
- Assure la compatibilité avant concaténation

#### 📊 **`video_analyzer.py`** - ANALYSE
- Analyse et score les segments vidéo
- Identifie les meilleurs moments

### 🔍 Modules de Détection
- **`face_detector.py`** - Reconnaissance et détection faciale
- **`text_detector.py`** - Détection et suppression de texte

### 🛠️ Utilitaires
- **`utils.py`** - Fonctions helper (gestion fichiers, temps, etc.)

## 📂 Dossiers

### `old_versions/`
Contient les anciennes versions et scripts de test pour référence.

### `__pycache__/`
Cache Python (ignoré par Git)

## 🚀 Utilisation

```bash
# Installation des dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run upload_video_mixer.py
```

## 🔄 Flux de Traitement

```
1. Upload des vidéos
       ↓
2. EXTRACTION (video_extractor.py)
   - Analyse des vidéos
   - Extraction des meilleurs clips
   - Redimensionnement au format 9:16
       ↓
3. NORMALISATION (video_normalizer.py)
   - Uniformisation des clips
   - Vérification de compatibilité
       ↓
4. ASSEMBLAGE (video_assembler.py)
   - Matérialisation des clips
   - Concaténation sécurisée
   - Ajout logo/audio/tagline
       ↓
5. Export vidéo finale
```

## 🏗️ Architecture Technique

```
upload_video_mixer.py
    │
    ├─→ video_extractor.py (EXTRACTION)
    │   ├── video_analyzer.py
    │   ├── face_detector.py
    │   └── text_detector.py
    │
    └─→ video_assembler.py (ASSEMBLAGE)
        └── video_normalizer.py
```

## ⚡ Points Clés

### Séparation des responsabilités
- **Extraction** : Trouve et extrait les meilleurs moments
- **Assemblage** : Combine les clips en vidéo finale

### Résolution du bug MoviePy
Le module `video_assembler` utilise la matérialisation systématique :
1. Chaque clip est écrit sur disque
2. Puis rechargé comme fichier indépendant
3. Élimine les problèmes de références cassées

### Noms explicites
- `video_extractor` → clairement pour l'extraction
- `video_assembler` → clairement pour l'assemblage
- Plus de confusion avec les multiples `video_processor_*`

## 🐛 Résolution de Problèmes

### Erreur `'NoneType' object has no attribute 'get_frame'`
✅ **Résolu** par la matérialisation dans `video_assembler.py`

### Clips de tailles différentes
✅ **Résolu** par la normalisation dans `video_normalizer.py`

### Problèmes de mémoire
✅ **Optimisé** avec libération agressive et limitation du nombre de clips

## 📝 Notes

- Les fichiers vidéo temporaires sont automatiquement nettoyés
- Le cache Python peut être supprimé sans risque
- Les anciennes versions sont conservées dans `old_versions/` pour référence
