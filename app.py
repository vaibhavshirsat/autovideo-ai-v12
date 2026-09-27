import os
import re
import json
import time
import shutil
import subprocess
from pathlib import Path

import streamlit as st

try:
    import higgsfield_client
except Exception:
    higgsfield_client = None

try:
    import requests
except Exception:
    requests = None

APP_DIR = Path(__file__).parent
WORK_DIR = APP_DIR / "workspace"
WORK_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="VAIBHAV AI Video Studio", page_icon="🎬", layout="wide")

st.markdown("""
<style>
:root { color-scheme: dark; }
.block-container { max-width: 1400px; padding-top: 1rem; }
.hero { padding: 24px 28px; border-radius: 22px; background: linear-gradient(135deg,#111827,#1f2937 55%,#111827); border:1px solid #374151; margin-bottom:18px; }
.hero h1 { margin:0; font-size:42px; letter-spacing:-1px; }
.hero p { margin:8px 0 0; color:#cbd5e1; font-size:16px; }
.card { padding:18px; border-radius:18px; border:1px solid #334155; background:#0f172a; margin-bottom:14px; }
.badge { display:inline-block; padding:5px 10px; border-radius:999px; background:#172554; color:#bfdbfe; font-size:12px; margin-right:6px; }
.small { color:#94a3b8; font-size:13px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🎬 VAIBHAV AI VIDEO STUDIO</h1>
<p>Prompt → Story Director → Detailed Shots → AI Images → Real I2V Motion → Native Audio → Final 9:16 Reel</p>
<span class="badge">REAL AI VIDEO</span><span class="badge">1080×1920</span><span class="badge">CINEMATIC</span><span class="badge">VAIBHAV AI TOP-RIGHT</span>
</div>
""", unsafe_allow_html=True)


def get_credentials():
    key = st.session_state.get("hf_key", "").strip()
    if key:
        return key
    env_key = os.getenv("HF_KEY", "").strip()
    if env_key:
        return env_key
    k = os.getenv("HF_API_KEY", "").strip()
    s = os.getenv("HF_API_SECRET", "").strip()
    if k and s:
        return f"{k}:{s}"
    return ""


def configure_sdk():
    if higgsfield_client is None:
        raise RuntimeError("higgsfield-client package is not installed.")
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Higgsfield API key is missing. Add HF_KEY as KEY_ID:KEY_SECRET in Streamlit Secrets or paste it in the sidebar.")
    # Official SDK reads HF_KEY from the environment.
    os.environ["HF_KEY"] = creds


def hf_subscribe(endpoint, arguments, status_box=None):
    configure_sdk()
    if status_box:
        status_box.info(f"Submitting {endpoint} …")
    result = higgsfield_client.subscribe(endpoint, arguments=arguments)
    if status_box:
        status_box.success("Generation completed")
    return result


def result_url(result, kind="video"):
    if not isinstance(result, dict):
        return None
    if kind == "video" and result.get("video"):
        v = result["video"]
        return v.get("url") if isinstance(v, dict) else v
    if kind == "image" and result.get("images"):
        first = result["images"][0]
        return first.get("url") if isinstance(first, dict) else first
    return None


def download_url(url, path):
    if requests is None:
        raise RuntimeError("requests package missing")
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    Path(path).write_bytes(r.content)
    return path


def sanitize(s):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s)[:80]


def make_storyboard(prompt, college, location, language, scenes, style, character):
    # This is intentionally deterministic and provider-independent. It avoids a fake 'AI story'
    # dependency just to create the production plan.
    base = prompt.strip()
    college_line = f"The institution is {college}. Show the exact college name prominently on a realistic exterior sign when appropriate." if college.strip() else "If a school/college is mentioned, show realistic signage."
    char = character.strip() or "a consistent young protagonist appropriate to the story"
    templates = [
        ("HOOK / ESTABLISHING", "wide cinematic establishing shot, strong visual hook, location identity, detailed environment"),
        ("CHARACTER INTRO", "medium shot introducing the main character, natural body movement, expressive face, detailed wardrobe"),
        ("ACTION", "dynamic tracking shot, meaningful physical action, realistic crowd/background motion, cinematic camera movement"),
        ("EMOTION", "close-up or intimate medium shot, emotional performance, subtle facial movement, natural lighting"),
        ("TURNING POINT", "dramatic reveal or decisive action, stronger camera movement, atmosphere and environmental detail"),
        ("ENDING", "heroic or emotional final composition, camera pull-back, memorable ending frame"),
        ("CTA / RESOLUTION", "clean final composition, visual closure, subtle movement, readable on-screen context"),
        ("EPILOGUE", "quiet cinematic final beat, environmental detail, soft camera motion"),
    ]
    out = []
    for i in range(scenes):
        name, camera = templates[i % len(templates)]
        detail = (
            f"{camera}. {college_line} Location: {location or 'story-appropriate location'}. "
            f"Language/context: {language}. Main character: {char}. "
            f"Visual style: {style}. Story premise: {base}. "
            "Photorealistic/cinematic detail, physically plausible anatomy, coherent wardrobe, consistent face, "
            "realistic lighting, depth of field, natural motion cues, no logos or random text, no watermark. "
            "Vertical 9:16 composition, subject framed safely for social media."
        )
        out.append({"shot": i + 1, "title": name, "prompt": detail})
    return out


def concat_videos(paths, output):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available on this machine. Install FFmpeg or use a deployment image that includes it.")
    list_file = WORK_DIR / "concat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for p in paths:
            # ffmpeg concat demuxer requires escaped single quotes.
            s = str(Path(p).resolve()).replace("'", "'\\''")
            f.write(f"file '{s}'\n")
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        # Re-encode when source parameters differ.
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-3000:])
    return output


def add_branding_and_exact_text(input_video, output_video, college, title, show_college, watermark):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return input_video
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    filters = []
    # Exact VAIBHAV AI watermark: only top-right.
    if watermark:
        safe_wm = watermark.replace("'", "\\'").replace(":", "\\:")
        filters.append(
            f"drawtext=fontfile={font}:text='{safe_wm}':fontcolor=white@0.90:fontsize=30:" 
            "box=1:boxcolor=black@0.35:boxborderw=10:x=w-tw-24:y=24"
        )
    # Post-production text overlay is used for exact spelling; this is more reliable than asking a video model to render text.
    if show_college and college.strip():
        txt = college.strip().replace("'", "\\'").replace(":", "\\:")
        filters.append(
            f"drawtext=fontfile={font}:text='{txt}':fontcolor=white:fontsize=46:box=1:boxcolor=black@0.50:boxborderw=16:" 
            "x=(w-tw)/2:y=h-190:enable='between(t,0,4.5)'"
        )
    if title.strip():
        txt = title.strip().replace("'", "\\'").replace(":", "\\:")
        filters.append(
            f"drawtext=fontfile={font}:text='{txt}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.35:boxborderw=12:" 
            "x=(w-tw)/2:y=95:enable='between(t,0,3.5)'"
        )
    if not filters:
        shutil.copy2(input_video, output_video)
        return output_video
    vf = ",".join(filters)
    cmd = [ffmpeg, "-y", "-i", str(input_video), "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_video)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-3000:])
    return output_video


def add_uploaded_bgm(video_path, bgm_path, output_path, volume=0.18):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg unavailable")
    cmd = [ffmpeg, "-y", "-i", str(video_path), "-stream_loop", "-1", "-i", str(bgm_path),
           "-filter_complex", f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
           "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-3000:])
    return output_path


# Sidebar
with st.sidebar:
    st.header("⚙️ Production")
    st.caption("Real generation requires a Higgsfield API credential. No fake static-video fallback is used.")
    st.text_input("Higgsfield HF_KEY", type="password", key="hf_key", placeholder="KEY_ID:KEY_SECRET")
    st.markdown("[Higgsfield API docs](https://open.higgsfield.ai/)")
    st.divider()
    scenes = st.slider("Scenes", 2, 8, 5)
    duration = st.select_slider("Seconds / scene", options=[3, 5, 10, 15], value=5)
    quality = st.selectbox("I2V engine", ["Kling 3.0 Pro", "Kling 3.0 Standard", "Kling 3.0 4K"], index=0)
    sound = st.toggle("Native AI sound", value=True)
    st.caption("Kling 3.0 I2V supports up to 15s per clip and optional sound.")
    watermark = st.text_input("Watermark", value="VAIBHAV AI")

left, right = st.columns([1.1, 0.9])
with left:
    st.subheader("1. 🎯 Story Brief")
    prompt = st.text_area("What video should I make?", height=150, placeholder="Example: A first-year student enters a famous Pune college, struggles on the first day, makes a friend, and ends with a powerful emotional moment.")
    c1, c2 = st.columns(2)
    with c1:
        college = st.text_input("College / Institution name", placeholder="e.g. Modern College of Arts, Science and Commerce")
        location = st.text_input("Location", value="Pune, Maharashtra")
        language = st.selectbox("Story / dialogue language", ["Marathi", "Hindi", "English", "Hinglish"])
    with c2:
        title = st.text_input("Video title", placeholder="Optional")
        character = st.text_input("Main character DNA", placeholder="e.g. 19-year-old Indian male student, curly black hair, blue backpack")
        style = st.selectbox("Visual style", ["Photorealistic cinematic", "High-end 3D animation", "Anime cinematic", "Documentary realism", "Indian commercial film"])
    show_college = st.checkbox("Add exact college name as post-production text", value=True)

with right:
    st.subheader("2. 🎵 Audio / Finishing")
    bgm = st.file_uploader("Optional background music (MP3/WAV)", type=["mp3", "wav", "m4a"])
    st.info("If Native AI sound is ON, each generated clip can include generated ambient/effect audio. Upload BGM if you want your own music layer.")
    st.markdown("**Final pipeline**")
    st.write("Prompt → Storyboard → 2K scene image → Real I2V → audio → concatenate → exact text → VAIBHAV AI watermark → MP4")

if "storyboard" not in st.session_state:
    st.session_state.storyboard = None

col_a, col_b = st.columns(2)
with col_a:
    if st.button("🧠 Generate Detailed Storyboard", use_container_width=True):
        if not prompt.strip():
            st.error("Prompt द्या.")
        else:
            st.session_state.storyboard = make_storyboard(prompt, college, location, language, scenes, style, character)
            st.success(f"{scenes} scenes तयार.")

if st.session_state.storyboard:
    st.subheader("3. 🎞️ Shot Director")
    for shot in st.session_state.storyboard:
        with st.expander(f"Shot {shot['shot']} — {shot['title']}", expanded=False):
            st.write(shot["prompt"])

with col_b:
    can_generate = bool(prompt.strip() and st.session_state.storyboard)
    if st.button("🚀 GENERATE REAL AI REEL", type="primary", disabled=not can_generate, use_container_width=True):
        try:
            configure_sdk()
            session = WORK_DIR / time.strftime("%Y%m%d_%H%M%S")
            session.mkdir(parents=True, exist_ok=True)
            status = st.status("Starting production…", expanded=True)
            shot_videos = []
            image_urls = []

            if quality == "Kling 3.0 Pro":
                i2v_endpoint = "kling-video/v3.0/pro/image-to-video"
            elif quality == "Kling 3.0 4K":
                i2v_endpoint = "kling-video/v3.0/4k/image-to-video"
            else:
                i2v_endpoint = "kling-video/v3.0/std/image-to-video"

            for shot in st.session_state.storyboard:
                status.write(f"🎨 Shot {shot['shot']}/{len(st.session_state.storyboard)} — generating detailed 2K image…")
                img_prompt = shot["prompt"] + " Do not place any brand logo or watermark in the image."
                img_res = hf_subscribe(
                    "bytedance/seedream/v4/text-to-image",
                    {
                        "prompt": img_prompt,
                        "resolution": "2K",
                        "aspect_ratio": "9:16",
                        "camera_fixed": False,
                    },
                    None,
                )
                img_url = result_url(img_res, "image")
                if not img_url:
                    raise RuntimeError(f"Shot {shot['shot']}: image generation returned no image URL. Raw response: {str(img_res)[:1500]}")
                image_urls.append(img_url)
                (session / f"shot_{shot['shot']}_image.url.txt").write_text(img_url, encoding="utf-8")

                status.write(f"🎥 Shot {shot['shot']}/{len(st.session_state.storyboard)} — real I2V motion…")
                motion_prompt = (
                    shot["prompt"] + " Animate naturally: realistic human motion, subtle facial expression, "
                    "natural cloth and hair movement, environmental motion, cinematic camera movement, "
                    "stable identity, no morphing, no extra limbs, no text distortion."
                )
                args = {
                    "sound": "on" if sound else "off",
                    "prompt": motion_prompt,
                    "duration": duration,
                    "cfg_scale": 0.5,
                    "image_url": img_url,
                    "multi_shots": False,
                }
                vid_res = hf_subscribe(i2v_endpoint, args, None)
                vid_url = result_url(vid_res, "video")
                if not vid_url:
                    raise RuntimeError(f"Shot {shot['shot']}: I2V returned no video URL. Raw response: {str(vid_res)[:1500]}")
                clip = session / f"shot_{shot['shot']}.mp4"
                download_url(vid_url, clip)
                shot_videos.append(clip)

            status.write("✂️ Joining real motion clips…")
            raw_final = session / "raw_reel.mp4"
            concat_videos(shot_videos, raw_final)

            branded = session / "VAIBHAV_AI_REEL.mp4"
            add_branding_and_exact_text(raw_final, branded, college, title, show_college, watermark)

            final = branded
            if bgm is not None:
                bgm_path = session / bgm.name
                bgm_path.write_bytes(bgm.getbuffer())
                mixed = session / "VAIBHAV_AI_REEL_FINAL.mp4"
                add_uploaded_bgm(final, bgm_path, mixed, volume=0.16)
                final = mixed

            status.update(label="✅ REAL AI REEL READY", state="complete")
            st.success("Done — हा static zoom/pan fallback नाही. प्रत्येक scene साठी actual AI-generated motion clip तयार झाला आहे.")
            st.video(str(final))
            st.download_button("⬇️ Download Final MP4", data=final.read_bytes(), file_name="VAIBHAV_AI_REEL.mp4", mime="video/mp4", use_container_width=True)
            st.caption(f"Production folder: {session}")
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.code("Check: HF_KEY = KEY_ID:KEY_SECRET, Higgsfield credits/access, and that the selected model is enabled on your account.")

st.divider()
st.markdown("### 🔐 Branding rule")
st.write("**VAIBHAV AI is added only in the top-right corner.** No character chest/back branding is generated by this app.")
st.markdown("### ⚠️ Important")
st.write("AI video models can still imperfectly render tiny signs/text inside generated footage. For the college name, this build adds an exact post-production overlay when enabled, so the spelling is deterministic.")
