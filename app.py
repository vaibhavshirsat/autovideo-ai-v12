import os, re, json, tempfile, subprocess, asyncio, wave, time, uuid, base64, requests, math
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AutoVideo AI — V12 STORY STUDIO", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 10% 0%,#102746 0,#06111f 35%,#040912 100%);color:#eef6ff}
.block-container{max-width:1280px;padding-top:1rem}
.hero{padding:24px;border:1px solid #1d5d8c;border-radius:22px;background:linear-gradient(135deg,#0b2440,#15102e);box-shadow:0 10px 40px #0005}
.badge{display:inline-block;padding:5px 10px;border-radius:999px;background:linear-gradient(90deg,#13b8ff,#b14cff);color:white;font-weight:800;font-size:12px}
.card{padding:16px;border:1px solid #21425f;border-radius:16px;background:#081522aa}
.small{color:#a9bdd0;font-size:13px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎬 AutoVideo AI <span class="badge">V12 STORY STUDIO</span></h1><div>Prompt → Viral Story → Master Character → Shot Bible → AI Images → Motion → Voice → Music → VAIBHAV → MP4</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔌 AI Providers")
    st.caption("Keys are entered at runtime only; do not commit secrets to GitHub.")
    hf_token = st.text_input("Hugging Face token", type="password", placeholder="hf_...")
    pollinations_key = st.text_input("Pollinations API key", type="password", placeholder="API key")
    runway_key = st.text_input("Runway API key", type="password")
    pixverse_key = st.text_input("PixVerse API key", type="password")
    pika_key = st.text_input("Pika API key", type="password")
    st.divider()
    st.subheader("🎯 Production mode")
    viral_mode = st.checkbox("🔥 Viral Story Mode", True)
    use_reference = st.checkbox("🧬 Use uploaded Master Character", False)
    st.info("V12 is built around a reusable Character Bible + shot-by-shot prompts. Paid motion providers remain optional; Cinematic Fallback is always available after image generation.")


def get_client(t):
    from huggingface_hub import InferenceClient
    return InferenceClient(api_key=t.strip())


def pollinations_image(key, prompt, width=1024, height=1024):
    url="https://gen.pollinations.ai/image/" + requests.utils.quote(prompt, safe="")
    params={"model":"flux","width":width,"height":height,"nologo":"true"}
    r=requests.get(url,params=params,headers={"Authorization":f"Bearer {key.strip()}"},timeout=180)
    r.raise_for_status()
    from PIL import Image
    return Image.open(__import__('io').BytesIO(r.content)).convert("RGB")


def pollinations_text(key, prompt, lang, n, viral):
    url="https://gen.pollinations.ai/v1/chat/completions"
    mode = "viral short-form director" if viral else "short-film director"
    system=f"""You are a {mode}. Return ONLY the exact fields requested. No JSON, markdown or quotes.
Fields: TITLE:, HOOK:, CHARACTER_DNA:, WORLD_DNA:, SCENE_1_NARRATION:, SCENE_1_VISUAL:, SCENE_1_CAMERA:, SCENE_1_MOTION:, SCENE_1_SFX: and continue through the requested scene count.
CHARACTER_DNA must be a compact immutable description of the recurring main character: species/person, age, face, body, hair/fur, outfit, colors, accessories, proportions.
WORLD_DNA must describe the recurring visual world, palette and lighting.
Every scene visual must explicitly preserve CHARACTER_DNA and WORLD_DNA and specify a concrete action. Avoid text, logos and watermarks.
Viral mode: hook within the first 2 seconds, escalating curiosity, emotional beat, visual surprise/twist, satisfying ending, and a loop-friendly final image.
Language: {lang}."""
    payload={"model":"openai-fast","messages":[{"role":"system","content":system},{"role":"user","content":f"Scenes: {n}; idea: {prompt}"}],"max_tokens":max(600,320*n)}
    r=requests.post(url,json=payload,headers={"Authorization":f"Bearer {key.strip()}"},timeout=120)
    r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]


def fallback_story(prompt, lang, n, viral=True):
    character = "a tiny adorable fluffy baby chick, round face, large expressive brown eyes, soft golden-yellow feathers, tiny orange feet, small sky-blue raincoat, small red satchel, childlike proportions"
    world = "lush colorful Indian village meadow, cinematic 3D animation, soft volumetric light, rich greens and warm golds, realistic rain and flowers, premium family-film look"
    narrs={
        "Marathi":["सगळे पळून गेले... पण हा छोटासा जीव थांबला.","त्याला पावसात एक छोटंसं जीव वाचवण्यासाठी धावताना काहीतरी दिसलं.","वादळ वाढत होतं, पण त्याने त्या जीवाला सोडलं नाही.","अचानक त्याला एक अनपेक्षित मार्ग दिसला.","एका छोट्या धाडसाने सगळं बदललं.","आणि शेवटी... ज्याला तो वाचवत होता, त्यानेच त्याला एक सुंदर भेट दिली."],
        "Hindi":["सब भाग गए... लेकिन यह छोटा सा जीव रुक गया।","बारिश में उसे किसी को बचाने का मौका दिखा।","तूफान बढ़ता गया, लेकिन उसने उसे अकेला नहीं छोड़ा।","तभी उसे एक अनपेक्षित रास्ता दिखाई दिया।","एक छोटी सी हिम्मत ने सब कुछ बदल दिया।","और आखिर में... जिसे उसने बचाया था, उसी ने उसे एक खूबसूरत तोहफा दिया।"],
        "English":["Everyone ran away... but this tiny hero stayed.","In the rain, he spotted someone who needed help.","The storm grew stronger, but he refused to leave.","Then he noticed a tiny unexpected way out.","One small act of courage changed everything.","And in the end... the one he saved gave him a beautiful surprise."],
        "Hinglish":["Sab bhaag gaye... lekin yeh chhota hero ruk gaya.","Rain mein usne kisi ko help ke liye struggle karte dekha.","Storm badhta gaya, par usne usse akela nahi chhoda.","Tabhi usse ek unexpected raasta dikha.","Ek chhoti si himmat ne sab kuch badal diya.","Aur end mein... jise usne bachaya, usne hi beautiful surprise diya."]}
    base_visual=[
        "opening hook: the tiny chick stands alone in heavy rain as a huge raindrop crashes near camera, shocked expression, immediate visual danger",
        "the same chick runs through a flower meadow toward a tiny butterfly trapped under a bent leaf, urgent action",
        "the same chick shields the butterfly with its blue raincoat while wind and rain intensify, emotional close-up",
        "the chick discovers a hollow tree glowing with warm light and carefully carries the butterfly toward safety, magical reveal",
        "the storm suddenly clears and golden sunlight floods the meadow, butterfly circles the chick, joyful reaction",
        "final close-up: chick smiles at camera as butterfly flies upward and reveals a rainbow, ending composition designed to loop back to rain"
    ]
    cameras=["fast push-in close-up","low tracking shot","orbit close-up","wide reveal then dolly-in","slow crane up","hero close-up with gentle pull-back"]
    motions=["blink, gasp, tiny body shake, raindrop splashes","run with quick tiny steps, wings balancing, camera tracks","coat flutters, chick leans forward, butterfly moves its wings","careful walking, head turns toward glow, camera follows","breathing settles, smile grows, butterfly circles","slow blink, smile, look upward, butterfly arcs through frame"]
    sfx=["rain impact, tiny gasp","footsteps, rain, wind","rain, wing flutter, heartbeat-like soft hit","wind drop, magical chime","birds, soft wind, warm sparkle","gentle wing flutter, soft chime, distant birds"]
    scenes=[]
    for i in range(n):
        j=i%6
        scenes.append({"narration":narrs.get(lang,narrs["English"])[j],"visual_prompt":f"{character}. {world}. {base_visual[j]}","camera":cameras[j],"motion":motions[j],"sfx":sfx[j]})
    return {"title":"The Tiny Hero","hook":narrs.get(lang,narrs["English"])[0],"character_dna":character,"world_dna":world,"scenes":scenes}


def parse_plan_content(content,n):
    lines=[x.strip() for x in content.splitlines() if x.strip()]
    data={"title":"","hook":"","character_dna":"","world_dna":"","scenes":[]}; temp={}
    for line in lines:
        if ":" not in line: continue
        k,v=line.split(":",1); k=k.strip().upper(); v=v.strip()
        m=re.fullmatch(r"SCENE_(\d+)_(NARRATION|VISUAL|CAMERA|MOTION|SFX)",k)
        if m:
            idx=int(m.group(1)); temp.setdefault(idx,{})
            field={"NARRATION":"narration","VISUAL":"visual_prompt","CAMERA":"camera","MOTION":"motion","SFX":"sfx"}[m.group(2)]
            temp[idx][field]=v
        elif k=="TITLE": data["title"]=v
        elif k=="HOOK": data["hook"]=v
        elif k=="CHARACTER_DNA": data["character_dna"]=v
        elif k=="WORLD_DNA": data["world_dna"]=v
    for i in sorted(temp):
        s=temp[i]
        if s.get("narration") and s.get("visual_prompt"):
            s.setdefault("camera","cinematic camera movement")
            s.setdefault("motion","natural continuous movement")
            s.setdefault("sfx","natural scene ambience")
            data["scenes"].append(s)
    if len(data["scenes"])<n or not data["character_dna"]: raise ValueError("Planner returned incomplete Character Bible or scenes")
    return data


def plan_story(hf,poll,prompt,lang,n,viral):
    if poll.strip():
        try: return parse_plan_content(pollinations_text(poll,prompt,lang,n,viral),n),"Pollinations"
        except Exception: pass
    if hf.strip():
        try:
            c=get_client(hf)
            system=f"""You are a viral short-video director. Return ONLY exact lines: TITLE, HOOK, CHARACTER_DNA, WORLD_DNA, then for every scene NARRATION, VISUAL, CAMERA, MOTION, SFX. No JSON/markdown. Character DNA must be immutable and reused in every visual. Viral mode={viral}. Visuals must be specific, cinematic and action-driven."""
            r=c.chat_completion(model="openai/gpt-oss-120b",messages=[{"role":"system","content":system},{"role":"user","content":f"Language: {lang}; scenes: {n}; idea: {prompt}"}],max_tokens=max(600,320*n))
            return parse_plan_content(getattr(r.choices[0].message,"content","") or "",n),"Hugging Face"
        except Exception: pass
    return fallback_story(prompt,lang,n,viral),"Fallback"


def make_image(hf,poll,prompt,width=1024,height=1024):
    final_prompt=prompt + ", premium cinematic 3D animated feature-film frame, coherent anatomy, expressive face, detailed materials, no text, no logo, no watermark"
    if poll.strip():
        return pollinations_image(poll,final_prompt,width,height)
    if hf.strip():
        c=get_client(hf); return c.text_to_image(prompt=final_prompt,model="black-forest-labs/FLUX.1-schnell")
    raise RuntimeError("No working image provider. Add a provider key or upload a Master Character image.")


def make_voice(text,lang):
    import edge_tts
    voices={"Marathi":"mr-IN-AarohiNeural","Hindi":"hi-IN-SwaraNeural","English":"en-IN-NeerjaNeural","Hinglish":"hi-IN-SwaraNeural"}
    out=tempfile.NamedTemporaryFile(delete=False,suffix=".mp3").name
    async def go(): await edge_tts.Communicate(text,voices.get(lang,"en-IN-NeerjaNeural"),rate="+0%",pitch="+0Hz").save(out)
    asyncio.run(go()); return out


def make_music(seconds):
    import numpy as np
    sr=44100; n=int(sr*seconds); t=np.arange(n)/sr
    sig=.018*np.sin(2*np.pi*220*t)+.012*np.sin(2*np.pi*277.18*t)+.008*np.sin(2*np.pi*329.63*t)
    fade=np.minimum(1,np.minimum(t,2))*np.minimum(1,(seconds-t)/2); sig*=np.clip(fade,0,1)
    out=tempfile.NamedTemporaryFile(delete=False,suffix=".wav").name
    with wave.open(out,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((sig*32767).astype(np.int16).tobytes())
    return out


def add_brand_to_image(im,brand):
    from PIL import ImageDraw,ImageFont
    im=im.convert("RGBA"); draw=ImageDraw.Draw(im)
    try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",max(18,im.width//34))
    except Exception: font=ImageFont.load_default()
    text=(brand or "VAIBHAV").strip() or "VAIBHAV"
    box=draw.textbbox((0,0),text,font=font,stroke_width=2); tw,th=box[2]-box[0],box[3]-box[1]
    x=(im.width-tw)//2; y=int(im.height*.67); pad=9
    draw.rounded_rectangle((x-pad,y-pad,x+tw+pad,y+th+pad),radius=10,fill=(0,0,0,105))
    draw.text((x,y),text,font=font,fill=(255,255,255,238),stroke_width=2,stroke_fill=(0,0,0,170))
    return im


def brand_video(input_video,brand,output_video):
    safe=(brand or "VAIBHAV").replace("\\","").replace("'","").replace(":"," ")
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    vf=f"drawtext=fontfile={font}:text='{safe}':x=w-tw-24:y=h-th-28:fontsize=34:fontcolor=white@0.88:borderw=2:bordercolor=black@0.65"
    subprocess.run(["ffmpeg","-y","-i",str(input_video),"-vf",vf,"-c:v","libx264","-preset","veryfast","-c:a","copy",str(output_video)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def render_static(images,narr,lang,total,aspect,res,music_on,brand):
    ff="ffmpeg"; work=Path(tempfile.mkdtemp(prefix="av12_static_"))
    if aspect=="9:16": W,H=(720,1280) if res=="720p" else (1080,1920)
    elif aspect=="1:1": W=H=720 if res=="720p" else 1080
    else: W,H=(1280,720) if res=="720p" else (1920,1080)
    per=total/len(images); clips=[]
    for i,(im,txt) in enumerate(zip(images,narr)):
        ip=work/f"scene_{i}.png"; im.save(ip); ap=make_voice(txt,lang); cp=work/f"clip_{i}.mp4"
        vf=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0007,1.06)':d=125:s={W}x{H}:fps=25"
        subprocess.run([ff,"-y","-loop","1","-i",str(ip),"-i",ap,"-t",str(per),"-vf",vf,"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(cp)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        clips.append(cp)
    concat=work/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    joined=work/"joined.mp4"; subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=joined
    if music_on:
        bed=make_music(total); final=work/"mixed.mp4"
        subprocess.run([ff,"-y","-i",str(base),"-i",bed,"-filter_complex","[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(final)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        base=final
    out=work/"final.mp4"; brand_video(base,brand,out); return out


def hf_ai_motion(token,image,prompt,duration):
    c=get_client(token); frames=max(25,min(49,int(duration*5)))
    return c.image_to_video(image=image,model="Wan-AI/Wan2.1-I2V-14B-720P",prompt=prompt+", natural continuous motion, cinematic camera, stable anatomy, consistent character",negative_prompt="flicker, warping, deformed face, extra limbs, duplicated objects, text, logo, watermark",num_frames=frames,num_inference_steps=20)


def runway_ai_motion(key,image,prompt,aspect):
    ratio="768:1280" if aspect=="9:16" else ("1280:768" if aspect=="16:9" else "1024:1024")
    b=__import__('io').BytesIO(); image.save(b,format="PNG"); data="data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
    payload={"model":"gen4.5","promptImage":data,"promptText":prompt+", smooth cinematic motion, consistent character, no text","ratio":ratio,"duration":5}
    h={"Authorization":f"Bearer {key.strip()}","Content-Type":"application/json","X-Runway-Version":"2024-11-06"}
    r=requests.post("https://api.dev.runwayml.com/v1/image_to_video",json=payload,headers=h,timeout=60); r.raise_for_status(); tid=r.json()["id"]
    for _ in range(90):
        q=requests.get(f"https://api.dev.runwayml.com/v1/tasks/{tid}",headers=h,timeout=30); q.raise_for_status(); d=q.json()
        if d.get("status")=="SUCCEEDED": return requests.get(d["output"][0],timeout=120).content
        if d.get("status") in ("FAILED","CANCELED"): raise RuntimeError(str(d))
        time.sleep(5)
    raise TimeoutError("Runway task timed out")


def render_motion_clips(clips,narr,lang,total,music_on,brand):
    ff="ffmpeg"; work=Path(tempfile.mkdtemp(prefix="av12_motion_")); per=total/len(clips); voiced=[]
    for i,(clip,txt) in enumerate(zip(clips,narr)):
        ap=make_voice(txt,lang); out=work/f"voice_{i}.mp4"
        subprocess.run([ff,"-y","-i",str(clip),"-i",ap,"-map","0:v:0","-map","1:a:0","-t",str(per),"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        voiced.append(out)
    concat=work/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in voiced),encoding="utf-8")
    joined=work/"joined.mp4"; subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    mixed=joined
    if music_on:
        bed=make_music(total); mixed=work/"mixed.mp4"
        subprocess.run([ff,"-y","-i",str(joined),"-i",bed,"-filter_complex","[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(mixed)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    final=work/"final.mp4"; brand_video(mixed,brand,final); return final


# ---------------- UI ----------------
left,right=st.columns([1.2,.8])
with left:
    prompt=st.text_area("✍️ Idea / Story",height=140,placeholder="A tiny monkey saves a lost child during a village festival...")
with right:
    lang=st.selectbox("🗣️ Language",["Marathi","Hindi","English","Hinglish"])
    scenes=st.selectbox("🎞️ Scenes",[3,4,5,6,7,8],index=2)
    duration=st.selectbox("⏱️ Duration (sec)",[15,20,30,45,60],index=2)
    aspect=st.selectbox("📐 Format",["9:16","16:9","1:1"],index=0)
    resolution=st.selectbox("📺 Output",["720p","1080p"],index=0)

st.markdown("### 🧬 Character Studio")
ref_file=st.file_uploader("Upload a Master Character image (optional)",type=["png","jpg","jpeg"],help="Use this to lock the visual identity you already like. If not uploaded, V12 creates a Master Character from the story plan.")
brand=st.text_input("🏷️ Exact brand", "VAIBHAV")
col1,col2,col3=st.columns(3)
with col1: image_engine=st.selectbox("🖼️ Image Engine",["Pollinations","Hugging Face"],index=0)
with col2: motion_engine=st.selectbox("🎥 Motion Engine",["Cinematic Fallback","Runway","Hugging Face"],index=0)
with col3: music=st.checkbox("🎵 Background music",True)

st.markdown("<div class='card'><b>V12 workflow</b><br><span class='small'>1. Viral hook → 2. Character Bible → 3. World Bible → 4. Shot-by-shot action → 5. Motion → 6. Voice + music → 7. Exact VAIBHAV overlay</span></div>",unsafe_allow_html=True)

if st.button("🚀 GENERATE V12 FINAL VIDEO",type="primary",use_container_width=True):
    if not prompt.strip(): st.error("Enter a story idea first."); st.stop()
    if not (pollinations_key.strip() or hf_token.strip()) and not ref_file:
        st.error("Add an image provider key, or upload a Master Character image."); st.stop()
    try:
        with st.status("Creating V12 story...",expanded=True) as status:
            st.write("🧠 Building viral story + Character Bible + World Bible...")
            story,planner=plan_story(hf_token,pollinations_key,prompt,lang,scenes,viral_mode)
            st.caption(f"Planner: {planner}")
            st.write(f"🧬 Character DNA: {story['character_dna']}")
            st.write(f"🌍 World DNA: {story['world_dna']}")

            # Master character
            if ref_file:
                from PIL import Image
                master=Image.open(ref_file).convert("RGB")
                st.write("🧬 Using uploaded Master Character reference...")
            else:
                st.write("🧬 Creating Master Character reference...")
                master_prompt=f"MASTER CHARACTER PORTRAIT. {story['character_dna']}. Neutral full-body 3/4 pose, centered, clean simple background, premium cinematic 3D animation, highly recognizable silhouette, consistent wardrobe and colors, no text, no logo, no watermark."
                master=make_image(hf_token if image_engine=="Hugging Face" else "",pollinations_key if image_engine=="Pollinations" else "",master_prompt)
            master=add_brand_to_image(master,brand)
            st.image(master,caption="Master Character — reuse this identity across the series",width=280)

            images=[]; narr=[]
            for i,s in enumerate(story["scenes"],1):
                st.write(f"🎨 Shot {i}/{scenes} — generating action frame...")
                shot_prompt=(f"SHOT {i}. CHARACTER DNA: {story['character_dna']}. WORLD DNA: {story['world_dna']}. "
                             f"ACTION: {s['visual_prompt']}. CAMERA: {s.get('camera','cinematic movement')}. "
                             f"MOTION INTENT: {s.get('motion','natural movement')}. Preserve exact character identity, outfit, colors, proportions and world style from the Character Bible. "
                             f"This is a single cinematic film frame, not a collage. No text, logos or watermark.")
                im=make_image(hf_token if image_engine=="Hugging Face" else "",pollinations_key if image_engine=="Pollinations" else "",shot_prompt)
                im=add_brand_to_image(im,brand); images.append(im); narr.append(s["narration"])

            if motion_engine=="Cinematic Fallback":
                st.write("🎬 Rendering cinematic camera motion + voice + music...")
                video=render_static(images,narr,lang,duration,aspect,resolution,music,brand)
            else:
                if motion_engine=="Runway":
                    if not runway_key.strip(): raise RuntimeError("Add the Runway API key first.")
                elif motion_engine=="Hugging Face" and not hf_token.strip():
                    raise RuntimeError("Add the Hugging Face token first.")
                clips=[]; per=max(4,min(10,duration/scenes))
                for i,(im,s) in enumerate(zip(images,story["scenes"]),1):
                    st.write(f"🎥 {motion_engine} motion {i}/{scenes}...")
                    if motion_engine=="Runway": raw=runway_ai_motion(runway_key,im,s["visual_prompt"]+", "+s.get("motion","natural motion"),aspect)
                    else: raw=hf_ai_motion(hf_token,im,s["visual_prompt"]+", "+s.get("motion","natural motion"),per)
                    cp=Path(tempfile.mkdtemp(prefix="av12_clip_"))/f"scene_{i}.mp4"; cp.write_bytes(raw); clips.append(cp)
                st.write("🎙️ Voice + 🎵 music + 🏷️ exact branding...")
                video=render_motion_clips(clips,narr,lang,duration,music,brand)
            status.update(label="✅ V12 FINAL VIDEO READY",state="complete")

        st.success("✅ V12 video ready — Character Bible + shot-driven visuals + voice + music + VAIBHAV. Captions OFF.")
        st.video(str(video))
        with open(video,"rb") as f: st.download_button("⬇️ Download FINAL MP4",f,"VAIBHAV_V12_FINAL.mp4","video/mp4",use_container_width=True)
        with st.expander("🧠 Story / Character / Shot Bible"): st.json(story)
    except Exception as e:
        st.error(f"Generation error: {e}")
        st.info("For the lowest-cost test: upload a Master Character image + use Cinematic Fallback. Real AI motion providers need their own API access/credits.")

st.markdown("---")
st.caption("V12 STORY STUDIO — Character Bible + World Bible + shot-by-shot prompts + optional AI motion. No captions. Exact VAIBHAV overlay is renderer-controlled.")
