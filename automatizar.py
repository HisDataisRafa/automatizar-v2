import streamlit as st
import requests
import io
from datetime import datetime
import json
import time
import os
import zipfile

# Inicialización del estado de la sesión para mantener los archivos y el caché
if 'current_generation' not in st.session_state:
    st.session_state.current_generation = {
        'zip_contents': None,
        'timestamp': None,
        'files_generated': False,
        'all_audio_files': [],  # Añadimos para mantener los archivos de audio
        'generation_progress': {  # Añadimos para mantener el progreso
            'current_fragment': 0,
            'total_fragments': 0,
            'fragments_completed': []
        }
    }

# [Las funciones split_text_for_tts y get_available_voices permanecen igual]

def generate_audio_with_retries(text, api_key, voice_id, stability, similarity, use_speaker_boost, 
                              fragment_number, retries=2, model_id="eleven_multilingual_v2"):
    """
    Genera audio usando la API de Eleven Labs con reintentos automáticos y caché
    """
    # Verificamos si este fragmento ya está en el caché
    cached_fragments = st.session_state.current_generation['generation_progress']['fragments_completed']
    if fragment_number in cached_fragments:
        cached_audios = [audio for audio in st.session_state.current_generation['all_audio_files'] 
                        if audio['filename'].startswith(str(fragment_number))]
        if cached_audios:
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
    
    # Si se generaron todos los resultados exitosamente, los guardamos en el caché
    if len(results) == 3:
        st.session_state.current_generation['generation_progress']['fragments_completed'].append(fragment_number)
        st.session_state.current_generation['all_audio_files'].extend(results)
    
    return results

def create_recovery_button():
    """
    Crea un botón para recuperar la última generación si existe
    """
    if (st.session_state.current_generation['all_audio_files'] and 
        not st.session_state.current_generation['files_generated']):
        if st.button("↻ Recuperar última generación"):
            # Recreamos los ZIP a partir de los archivos guardados
            st.session_state.current_generation['zip_contents'] = create_zip_files_by_version(
                st.session_state.current_generation['all_audio_files']
            )
            st.session_state.current_generation['timestamp'] = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.current_generation['files_generated'] = True
            st.rerun()

def main():
    st.title("🎙️ Generador de Audio con Eleven Labs")
    st.write("Divide tu texto y genera audio de alta calidad con reintentos automáticos")
    
    # [La configuración en la barra lateral permanece igual]
    
    # Añadimos el botón de recuperación
    create_recovery_button()
    
    # [El resto del código de configuración permanece igual hasta el botón de procesar]
    
    if st.button("Procesar texto y generar audios"):
        if not text_input or not api_key:
            st.warning("Por favor ingresa el texto y la API key.")
            return
        
        fragments = split_text_for_tts(text_input, max_chars)
        
        # Guardamos la información del progreso
        st.session_state.current_generation['generation_progress']['total_fragments'] = len(fragments)
        st.session_state.current_generation['generation_progress']['current_fragment'] = 0
        st.session_state.current_generation['all_audio_files'] = []
        st.session_state.current_generation['generation_progress']['fragments_completed'] = []
        
        st.info(f"Se generarán {len(fragments)} fragmentos, con 3 versiones cada uno (total: {len(fragments) * 3} archivos)")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_audio_files = []
        total_generations = len(fragments) * 3
        current_progress = 0
        
        for i, fragment in enumerate(fragments, 1):
            status_text.text(f"Generando fragmento {i}/{len(fragments)} (con reintentos)...")
            st.session_state.current_generation['generation_progress']['current_fragment'] = i
            
            audio_results = generate_audio_with_retries(
                fragment,
                api_key,
                voice_id,
                stability,
                similarity,
                use_speaker_boost,
                i
            )
            
            all_audio_files.extend(audio_results)
            current_progress += 3
            progress_bar.progress(current_progress / total_generations)
            
            with st.expander(f"Fragmento {i}"):
                st.write(fragment)
                for result in audio_results:
                    st.audio(result['content'], format="audio/mp3")
                    st.caption(f"Versión: {result['filename']}")
        
        status_text.text("¡Proceso completado! Preparando archivos ZIP...")
        
        if all_audio_files:
            # Guardamos los resultados en el estado de la sesión
            st.session_state.current_generation.update({
                'zip_contents': create_zip_files_by_version(all_audio_files),
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'files_generated': True,
                'all_audio_files': all_audio_files
            })
    
    # Mostrar los botones de descarga si hay archivos generados
    if st.session_state.current_generation['files_generated']:
        st.subheader("📥 Descargar archivos generados")
        
        # [El código de los botones de descarga permanece igual]

if __name__ == "__main__":
    main()
