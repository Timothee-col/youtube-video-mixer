"""
Fix alternatif avec nest_asyncio
"""
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

import asyncio
import atexit

def cleanup_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()
    except:
        pass

# Enregistrer le cleanup
atexit.register(cleanup_event_loop)
