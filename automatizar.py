import streamlit as st
import requests
import io
from datetime import datetime
import json
import time
import os
import zipfile

# Inicialización del estado de la sesión para el historial
if 'generation_history' not in st.session_state:
    st.session_state.generation_history = []

def save_to_history(audio_files, text_input, timestamp):
    """
    Guarda una generación en el historial de la sesión.
    Almacena los archivos de audio y la información relacionada.
    """
    history_entry = {
        'timestamp': timestamp,
        'text': text_input,
        'audio_files': audio_files,
        'fragments_count': len(set([file['filename'][:-5] for file in audio_files])) # Número único de fragmentos
    }
    st.session_state.generation_history.insert(0, history_entry)  # Añade al inicio para mostrar más reciente primero

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
    
    for audio in audio_files:
        version = audio['filename'][-5]
        files_by_version[version].append(audio)
    
    zip_contents = {}
    for version, files in files_by_version.items():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for audio in files:
                new_filename = f"{audio['filename'][:-5]}.mp3"
                zip_file.writestr(new_filename, audio['content'])
        
        zip_contents[version] = zip_buffer.getvalue()
    
    return zip_contents

def display_download_buttons(zip_contents, timestamp):
    """
    Muestra los botones de descarga para cada versión
    """
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

def display_history():
    """
    Muestra el historial de generaciones anteriores
    """
    if st.session_state.generation_history:
        st.header("📜 Historial de Generaciones")
        for i, entry in enumerate(st.session_state.generation_history):
            with st.expander(f"Generación {entry['timestamp']} - {entry['fragments_count']} fragmentos"):
                st.text_area("Texto original", entry['text'], height=100, disabled=True)
                
                # Creamos los ZIPs para esta entrada del historial
                zip_contents = create_zip_files_by_version(entry['audio_files'])
                
                # Mostramos los botones de descarga
                st.subheader("Descargar archivos")
                display_download_buttons(zip_contents, entry['timestamp'])
                
                # Previsualización de fragmentos
                st.subheader("Previsualización de fragmentos")
                fragments_dict = {}
                for audio in entry['audio_files']:
                    fragment_num = audio['filename'][:-5]  # Removemos la letra de versión
                    if fragment_num not in fragments_dict:
                        fragments_dict[fragment_num] = []
                    fragments_dict[fragment_num].append(audio)
                
                for fragment_num, audios in sorted(fragments_dict.items()):
                    with st.expander(f"Fragmento {fragment_num}"):
                        st.write(audios[0]['text'])  # Mostramos el texto del fragmento
                        for audio in audios:
                            st.audio(audio['content'], format="audio/mp3")
                            st.caption(f"Versión: {audio['filename'][-5]}")

def main():
    st.title("🎙️ Generador de Audio con Eleven Labs")
    st.write("Divide tu texto y genera audio de alta calidad con reintentos automáticos")
    
    # [La configuración permanece igual hasta el botón de procesamiento]
    
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
        
        status_text.text("¡Proceso completado! Preparando archivos ZIP...")
        
        if all_audio_files:
            # Generamos un timestamp único para esta generación
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Guardamos en el historial
            save_to_history(all_audio_files, text_input, timestamp)
            
            # Creamos y mostramos los botones de descarga para la generación actual
            zip_contents = create_zip_files_by_version(all_audio_files)
            st.subheader("📥 Descargar archivos generados")
            display_download_buttons(zip_contents, timestamp)
            
            st.success(f"Se han generado {len(all_audio_files)} archivos de audio en total, organizados en 3 ZIP separados.")
    
    # Mostramos el historial después de la generación
    display_history()

if __name__ == "__main__":
    main()
