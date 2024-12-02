import streamlit as st
import requests
import io
from datetime import datetime
import json
import time
import os
import zipfile

def split_text_for_tts(text, max_chars=250):
    """
    Divide el texto en fragmentos más pequeños respetando:
    1. Puntos finales
    2. Máximo de caracteres
    3. Estructura de párrafos
    4. División por comas en oraciones largas
    """
    # Dividimos el texto en párrafos, eliminando líneas vacías
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    fragments = []
    current_fragment = ""
    
    for paragraph in paragraphs:
        # Si el párrafo completo cabe en el límite, lo añadimos directamente
        if len(paragraph) <= max_chars:
            fragments.append(paragraph)
            continue
        
        # Dividimos el párrafo en oraciones
        sentences = [s.strip() + '.' for s in paragraph.replace('. ', '.').split('.') if s.strip()]
        
        for sentence in sentences:
            # Si la oración es más larga que el máximo, la dividimos por comas
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
            
            # Si la oración actual más el fragmento actual exceden el límite
            elif len(current_fragment + sentence) > max_chars:
                if current_fragment:
                    fragments.append(current_fragment.strip())
                current_fragment = sentence
            else:
                current_fragment = (current_fragment + " " + sentence).strip()
        
        # Añadimos el último fragmento del párrafo si existe
        if current_fragment:
            fragments.append(current_fragment)
            current_fragment = ""
    
    # Añadimos el último fragmento si queda alguno
    if current_fragment:
        fragments.append(current_fragment)
    
    return fragments

def generate_audio_with_retries(text, api_key, voice_id, stability, similarity, use_speaker_boost, 
                              fragment_number, retries=2, model_id="eleven_multilingual_v2"):
    """
    Genera audio usando la API de Eleven Labs con reintentos automáticos en caso de fallos
    """
    results = []
    letters = ['a', 'b', 'c']  # Para nombrar los archivos: 1a, 1b, 1c
    
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
                # Pausa entre intentos para evitar límites de la API
                time.sleep(10.5)
            else:
                st.warning(f"Error en intento {attempt + 1}: {response.status_code}")
        except Exception as e:
            st.error(f"Error en la solicitud: {str(e)}")
    
    return results

def get_available_voices(api_key):
    """
    Obtiene la lista de voces disponibles de Eleven Labs
    """
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            voices = response.json()["voices"]
            return {voice["name"]: voice["voice_id"] for voice in voices}
        return {}
    except:
        return {}

def create_zip_files_by_version(audio_files):
    """
    Crea archivos ZIP separados para cada versión (a, b, c)
    Retorna un diccionario con los contenidos de cada ZIP
    """
    files_by_version = {
        'a': [],
        'b': [],
        'c': []
    }
    
    # Clasificamos cada archivo según su versión
    for audio in audio_files:
        version = audio['filename'][-5]  # Obtiene la letra de la versión
        files_by_version[version].append(audio)
    
    # Creamos un ZIP para cada versión
    zip_contents = {}
    for version, files in files_by_version.items():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for audio in files:
                # Renombramos los archivos para quitar la letra de versión
                new_filename = f"{audio['filename'][:-5]}.mp3"
                zip_file.writestr(new_filename, audio['content'])
        
        zip_contents[version] = zip_buffer.getvalue()
    
    return zip_contents

def main():
    st.title("🎙️ Generador de Audio con Eleven Labs")
    st.write("Divide tu texto y genera audio de alta calidad con reintentos automáticos")
    
    # Configuración en la barra lateral
    st.sidebar.header("Configuración")
    
    # Explicación del proceso
    st.sidebar.markdown("""
    ### 🔄 Sistema de reintentos
    - Cada fragmento se generará 3 veces
    - Los archivos se nombrarán: 1a, 1b, 1c, 2a, 2b, 2c, etc.
    - Al final se descargará un ZIP con todos los audios
    """)
    
    # Configuración de la API y parámetros
    api_key = st.sidebar.text_input("API Key de Eleven Labs", type="password")
    
    max_chars = st.sidebar.number_input("Máximo de caracteres por fragmento", 
                                      min_value=100, 
                                      max_value=500, 
                                      value=250)
    
    # Configuración del modelo
    model_id = "eleven_multilingual_v2"
    st.sidebar.markdown("""
    **Modelo:** Eleven Multilingual v2
    - Soporta 29 idiomas
    - Ideal para voiceovers y audiolibros
    """)
    
    # Parámetros de voz
    stability = st.sidebar.slider("Stability", 
                                min_value=0.0, 
                                max_value=1.0, 
                                value=0.5,
                                step=0.01)
    
    similarity = st.sidebar.slider("Similarity", 
                                 min_value=0.0, 
                                 max_value=1.0, 
                                 value=0.75,
                                 step=0.01)
                                 
    use_speaker_boost = st.sidebar.checkbox("Speaker Boost", value=True)
    
    # Obtener y seleccionar voces disponibles
    if api_key:
        voices = get_available_voices(api_key)
        if voices:
            selected_voice_name = st.sidebar.selectbox("Seleccionar voz", 
                                                     list(voices.keys()))
            voice_id = voices[selected_voice_name]
        else:
            st.sidebar.error("No se pudieron cargar las voces. Verifica tu API key.")
            return
    
    # Área principal para el texto
    text_input = st.text_area("Ingresa tu texto", height=200)
    
    # Procesamiento principal
    if st.button("Procesar texto y generar audios"):
        if not text_input or not api_key:
            st.warning("Por favor ingresa el texto y la API key.")
            return
        
        fragments = split_text_for_tts(text_input, max_chars)
        st.info(f"Se generarán {len(fragments)} fragmentos, con 3 versiones cada uno (total: {len(fragments) * 3} archivos)")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_audio_files = []
        total_generations = len(fragments) * 3
        current_progress = 0
        
        # Generación de audio para cada fragmento
        for i, fragment in enumerate(fragments, 1):
            status_text.text(f"Generando fragmento {i}/{len(fragments)} (con reintentos)...")
            
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
            
            # Mostrar preview del fragmento actual
            with st.expander(f"Fragmento {i}"):
                st.write(fragment)
                for result in audio_results:
                    st.audio(result['content'], format="audio/mp3")
                    st.caption(f"Versión: {result['filename']}")
        
        status_text.text("¡Proceso completado! Preparando archivos ZIP...")
        
        # Crear y ofrecer descarga de los ZIPs separados
        if all_audio_files:
            zip_contents = create_zip_files_by_version(all_audio_files)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Creamos columnas para organizar los botones de descarga
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="⬇️ Descargar versión A",
                    data=zip_contents['a'],
                    file_name=f"audios_versionA_{timestamp}.zip",
                    mime="application/zip"
                )
            
            with col2:
                st.download_button(
                    label="⬇️ Descargar versión B",
                    data=zip_contents['b'],
                    file_name=f"audios_versionB_{timestamp}.zip",
                    mime="application/zip"
                )
            
            with col3:
                st.download_button(
                    label="⬇️ Descargar versión C",
                    data=zip_contents['c'],
                    file_name=f"audios_versionC_{timestamp}.zip",
                    mime="application/zip"
                )
            
            st.success(f"Se han generado {len(all_audio_files)} archivos de audio en total, organizados en 3 ZIP separados.")

if __name__ == "__main__":
    main()
