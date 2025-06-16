import os
import re
import tempfile
import requests
import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pathlib import Path

# Pegando chave da API Pexels da variável ambiente
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
if not PEXELS_API_KEY:
    st.error("⚠️ Configure a variável de ambiente PEXELS_API_KEY no Secrets da Streamlit Cloud.")
    st.stop()

st.title("🎬 Gerador de vídeo básico com Pexels e MoviePy")

script_text = st.text_area("Cole seu roteiro (separe cenas por linhas em branco)", height=300)
wpm = st.number_input("Palavras por minuto", min_value=50, max_value=300, value=150, step=10)

def split_script(text):
    # Divide o texto por linhas em branco (cenas)
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]

def estimate_duration(text, wpm):
    words = len(text.split())
    return max(2, words / (wpm / 60))  # mínimo 2 segundos

def pexels_search(query):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        st.error(f"Erro na busca Pexels: {resp.status_code}")
        return []
    return resp.json().get("videos", [])

def download_video(url, out_path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

def make_clip(video_path, duration):
    clip = VideoFileClip(str(video_path))
    return clip.subclip(0, min(duration, clip.duration))

if st.button("Gerar vídeo") and script_text:
    scenes = split_script(script_text)
    st.write(f"🎞️ Cenas detectadas: {len(scenes)}")

    clips = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, scene in enumerate(scenes, 1):
            duration = estimate_duration(scene, wpm)
            query = " ".join(scene.split()[:5])  # usa as 5 primeiras palavras como busca
            st.write(f"Cena {i}: '{query}' - duração estimada: {duration:.1f}s")

            videos = pexels_search(query)
            if not videos:
                st.warning(f"Nenhum vídeo encontrado para cena {i}")
                continue

            video_url = videos[0]["video_files"][0]["link"]
            video_path = Path(tmpdir) / f"scene_{i}.mp4"
            download_video(video_url, video_path)
            clip = make_clip(video_path, duration)
            clips.append(clip)

        if clips:
            final_clip = concatenate_videoclips(clips, method="compose")
            output_path = Path(tmpdir) / "final_video.mp4"
            final_clip.write_videofile(str(output_path), fps=24, codec="libx264", audio=False)
            st.video(str(output_path))
            with open(output_path, "rb") as f:
                st.download_button("Download do vídeo", f, file_name="video_gerado.mp4")
        else:
            st.error("Não foi possível gerar vídeo - nenhuma cena com clipe válido.")

