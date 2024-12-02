import streamlit as st
import requests
import io
from datetime import datetime
import json
import time
import os
import zipfile

# Inicialización completa y correcta del estado de la sesión
if 'current_generation' not in st.session_state:
    # Creamos una estructura completa con todos los campos necesarios
    st.session_state.current_generation = {
        'zip_contents': None,
        'timestamp': None,
        'files_generated': False,
        'all_audio_files': [],  # Inicializamos como lista vacía
        'generation_progress': {
            'current_fragment': 0,
            'total_fragments': 0,
            'fragments_completed': []
        }
    }

def split_text_for_tts(text, max_chars=250):
    """
    Divide el texto en fragmentos más pequeños respetando:
    1. Puntos finales
    2. Máximo de caracteres
    3. Estructura de párrafos
    4. División por comas en oraciones largas
    """
    # [El resto de la función permanece igual]
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    fragments = []
    current_fragment = ""
    
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            fragments.append(paragraph)
            continue
            
        sentences = [s.strip() + '.' for s in paragraph.replace('. ', '.').split('.') if s.strip()]
        
        for sentence in sentences:
            if len(sentence) > max_chars:
                parts = sentence.split(',')
                current_part = ""
                
                for part in parts:
                    part = part.strip()
                    if len(current_part) + len(part) + 2 <= max_chars:
                        current_part = (current_part + ", " + part).strip(", ")
                    else:
                        if current_part:
                            fragments.append(current_part + ".")
                        current_part = part
                
                if current_part:
                    fragments.append(current_part + ".")
                    
            elif len(current_fragment + sentence) > max_chars:
                if current_fragment:
                    fragments.append(current_fragment.strip())
                current_fragment = sentence
            else:
                current_fragment = (current_fragment + " " + sentence).strip()
        
        if current_fragment:
            fragments.append(current_fragment)
            current_fragment = ""
    
    if current_fragment:
        fragments.append(current_fragment)
    
    return fragments

def generate_audio_with_retries(text, api_key, voice_id, stability, similarity, use_speaker_boost, 
                              fragment_number, retries=2, model_id="eleven_multilingual_v2"):
    """
    Genera audio usando la API de Eleven Labs con reintentos automáticos y sistema de caché
    """
    # Verificación de caché mejorada
    cached_fragments = st.session_state.current_generation['generation_progress']['fragments_completed']
    if fragment_number in cached_fragments:
        # Buscamos en los archivos de audio guardados
        cached_audios = [
            audio for audio in st.session_state.current_generation['all_audio_files'] 
            if audio['filename'].startswith(str(fragment_number))
        ]
        if len(cached_audios) == 3:  # Verificamos que tengamos las tres versiones
            return cached_audios

    results = []
    letters = ['a', 'b', 'c']

    for attempt in range(retries + 1):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity,
                "style": 0,
                "use_speaker_boost": use_speaker_boost
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                filename = f"{fragment_number}{letters[attempt]}.mp3"
                results.append({
                    'content': response.content,
                    'filename': filename,
                    'text': text
                })
                time.sleep(5.5)
            else:
                st.warning(f"Error en intento {attempt + 1}: {response.status_code}")
        except Exception as e:
            st.error(f"Error en la solicitud: {str(e)}")
    
    # Actualizamos el caché solo si obtuvimos todas las versiones
    if len(results) == 3:
        st.session_state.current_generation['generation_progress']['fragments_completed'].append(fragment_number)
        st.session_state.current_generation['all_audio_files'].extend(results)
    
    return results

def create_recovery_button():
    """
    Crea un botón para recuperar la última generación
    """
    # Verificación segura del estado de la sesión
    has_audio_files = len(st.session_state.current_generation.get('all_audio_files', [])) > 0
    is_generated = st.session_state.current_generation.get('files_generated', False)
    
    if has_audio_files and not is_generated:
        if st.button("↻ Recuperar última generación"):
            # Recreamos los ZIP a partir de los archivos guardados
            st.session_state.current_generation['zip_contents'] = create_zip_files_by_version(
                st.session_state.current_generation['all_audio_files']
            )
            st.session_state.current_generation['timestamp'] = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.current_generation['files_generated'] = True
            st.rerun()

def main():
    # [El resto del código permanece igual, incluyendo la interfaz de usuario y la lógica de generación]
    pass

if __name__ == "__main__":
    main()
