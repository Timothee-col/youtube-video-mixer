"""
Fix pour l'erreur "Event loop is closed" avec Streamlit
"""
import asyncio
import sys
from asyncio import events

def patch_event_loop():
    """Patch pour éviter l'erreur 'Event loop is closed'"""
    if sys.platform.startswith('win'):
        # Windows specific
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Forcer la création d'un nouveau loop si l'ancien est fermé
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop

# Monkey patch pour Streamlit
original_get_event_loop = events.get_event_loop

def patched_get_event_loop():
    try:
        loop = original_get_event_loop()
        if loop.is_closed():
            return patch_event_loop()
        return loop
    except RuntimeError:
        return patch_event_loop()

events.get_event_loop = patched_get_event_loop
