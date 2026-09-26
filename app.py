
import os, re, json, tempfile, subprocess, asyncio, wave
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AutoVideo AI — V10 FINAL", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 10% 0%,#102746 0,#06111f 35%,#040912 100%);color:#eef6ff}
.block-container{max-width:1250px;padding-top:1.2rem}
.hero{padding:22px 24px;border:1px solid #1d5d8c;border-radius:20px;background:linear-gradient(135deg,#0b2440,#12102c)}
.badge{display:inline-block;padding:5px 10px;border-radius:999px;background:linear-gradient(90deg,#13b8ff,#b14cff);color:white;font-weight:700;font-size:12px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎬 AutoVideo AI <span class="badge">V10 FINAL</span></h1><div>Prompt → Story → Character → Motion → Voice → Music → MP4</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🆓 Free AI Connection")
    st.caption("No OpenAI API required.")
    token = st.text_input("Hugging Face Access Token", type="password", placeholder="hf_...")
    if st.button("🔌 Test Connection", use_container_width=True):
        if not token.strip():
            st.error("Enter your Hugging Face token.")
        else:
            try:
                from huggingface_hub import InferenceClient
                c = InferenceClient(api_key=token.strip())
                r = c.chat_completion(
                    model="openai/gpt-oss-120b",
                    messages=[{"role":"user","content":"Reply exactly OK"}],
                    max_tokens=16,
                )
                content = getattr(r.choices[0].message, "content", None) or ""
                st.success("✅ Text AI connected" if content.strip() else "✅ Provider responded")
            except Exception as e:
                st.error(f"Connection failed: {e}")
    st.divider()
    st.info("V10 has AI story planning, optional real AI motion, voice, music and automatic VAIBHAV branding. Captions are OFF.")
    st.caption("Start with 2 scenes / 15 sec / 720p. AI Motion may consume provider credits; fallback mode uses local cinematic motion.")

def get_client(t):
    from huggingface_hub import InferenceClient
    return InferenceClient(api_key=t.strip())

def fallback_story(prompt, lang, n):
    # Deterministic fallback means a provider returning empty/malformed text can never kill the whole render.
    base = [
        ("सुरुवात", "एक साधा भारतीय शहरातील सकाळचा दृश्य, छोटा चहाचा स्टॉल, मेहनती तरुण काम करताना, cinematic warm light"),
        ("मेहनत", "तोच तरुण गर्दीत ग्राहकांना चहा देताना, चेहऱ्यावर थकवा पण आत्मविश्वास, realistic Indian street scene"),
        ("स्वप्न", "रात्री छोट्या खोलीत वहीत व्यवसायाची कल्पना लिहिताना तरुण, खिडकीतून शहराचे दिवे, emotional cinematic lighting"),
        ("संघर्ष", "पावसात तो तरुण आपली छोटी चहाची गाडी सांभाळताना, कठीण परिस्थिती पण हार न मानणारा चेहरा"),
        ("यश", "काही वर्षांनी स्वतःच्या सुंदर छोट्या कॅफेच्या बाहेर उभा असलेला तोच तरुण, सकाळचे golden light"),
        ("शेवट", "कॅफेच्या दारात ग्राहकांचे स्वागत करणारा यशस्वी तरुण, समाधानाचे हास्य, uplifting cinematic ending"),
    ]
    nar = [
        "स्वप्न मोठं असण्यासाठी सुरुवात मोठी असण्याची गरज नसते.",
        "तो रोज मेहनत करत राहिला आणि प्रत्येक दिवसातून काहीतरी शिकत गेला.",
        "अडचणी आल्या, पण त्याने आपल्या स्वप्नावरचा विश्वास सोडला नाही.",
        "कधी कधी प्रवास कठीण असतो, पण थांबणं हा पर्याय नसतो.",
        "वर्षांच्या मेहनतीनंतर त्याचं छोटंसं स्वप्न एका सुंदर कॅफेमध्ये बदललं.",
        "आज त्याच्याकडे फक्त व्यवसाय नाही, तर स्वतःच्या मेहनतीची एक प्रेरणादायी गोष्ट आहे.",
    ]
    out=[]
    for i in range(n):
        title, visual = base[i % len(base)]
        text = nar[i % len(nar)]
        if lang == "Hindi":
            text = ["बड़ा सपना देखने के लिए बड़ी शुरुआत जरूरी नहीं होती।","वह हर दिन मेहनत करता रहा और सीखता रहा।","मुश्किलें आईं, लेकिन उसने अपना भरोसा नहीं छोड़ा।","रास्ता कठिन था, फिर भी उसने रुकना नहीं चुना।","सालों की मेहनत के बाद उसका छोटा सपना एक खूबसूरत कैफे बन गया।","आज उसके पास सिर्फ कारोबार नहीं, अपनी मेहनत की प्रेरणादायक कहानी है।"][i % 6]
        elif lang == "English":
            text = ["A big dream does not need a big beginning.","He kept working every day and learning from every challenge.","Difficult days came, but he never gave up on his dream.","The journey was hard, but stopping was never an option.","Years of hard work turned his small dream into a beautiful cafe.","He built more than a business; he built a story of persistence."][i % 6]
        elif lang == "Hinglish":
            text = ["Bada dream dekhne ke liye big beginning zaroori nahi hoti.","Woh har din mehnat karta raha aur seekhta raha.","Problems aayi, lekin usne apna confidence nahi chhoda.","Journey tough thi, par rukna option nahi tha.","Years ki mehnat se uska small dream ek beautiful cafe ban gaya.","Aaj uske paas business ke saath apni mehnat ki inspiring story bhi hai."][i % 6]
        out.append({"narration": text, "visual_prompt": visual + ", no text, no captions, no logos, no watermark"})
    return {"title":"मेहनती स्वप्न","hook":"छोटी सुरुवात, मोठं स्वप्न.","scenes":out}

def plan_story(t, prompt, lang, n):
    try:
        c=get_client(t)
        system="""You are a short-video director.
Return ONLY these exact lines, one field per line:
TITLE: ...
HOOK: ...
SCENE_1_NARRATION: ...
SCENE_1_VISUAL: ...
SCENE_2_NARRATION: ...
SCENE_2_VISUAL: ...
Continue to the requested scene count.
Never use JSON, markdown, quotes around fields, or multi-line field values.
Narration must be natural spoken language. Visual prompts must be distinct and contain no text/logos/watermarks."""
        r=c.chat_completion(
            model="openai/gpt-oss-120b",
            messages=[{"role":"system","content":system},
                      {"role":"user","content":f"Language: {lang}; scenes: {n}; idea: {prompt}"}],
            max_tokens=max(256, 180*n),
        )
        content = getattr(r.choices[0].message, "content", None)
        if not content or not content.strip():
            raise ValueError("AI planner returned an empty response")
        lines=[x.strip() for x in content.splitlines() if x.strip()]
        data={"title":"","hook":"","scenes":[]}
        temp={}
        for line in lines:
            if ":" not in line: continue
            k,v=line.split(":",1); k=k.strip().upper(); v=v.strip()
            m=re.fullmatch(r"SCENE_(\d+)_(NARRATION|VISUAL)",k)
            if m:
                idx=int(m.group(1))
                temp.setdefault(idx,{})
                temp[idx]["narration" if m.group(2)=="NARRATION" else "visual_prompt"]=v
            elif k=="TITLE": data["title"]=v
            elif k=="HOOK": data["hook"]=v
        for i in sorted(temp):
            if temp[i].get("narration") and temp[i].get("visual_prompt"):
                data["scenes"].append(temp[i])
        if len(data["scenes"]) < n:
            raise ValueError(f"AI planner returned {len(data['scenes'])}/{n} complete scenes")
        return data, "AI"
    except Exception:
        return fallback_story(prompt, lang, n), "Fallback"

def make_image(t, prompt):
    c=get_client(t)
    return c.text_to_image(
        prompt=prompt + ", cinematic composition, detailed Indian environment, strong subject, natural lighting, no text, no logo, no watermark",
        model="black-forest-labs/FLUX.1-schnell"
    )

def make_voice(text, lang):
    import edge_tts
    voices={"Marathi":"mr-IN-AarohiNeural","Hindi":"hi-IN-SwaraNeural","English":"en-IN-NeerjaNeural","Hinglish":"hi-IN-SwaraNeural"}
    out=tempfile.NamedTemporaryFile(delete=False,suffix=".mp3").name
    async def go():
        await edge_tts.Communicate(text, voices.get(lang,"en-IN-NeerjaNeural"), rate="+0%", pitch="+0Hz").save(out)
    asyncio.run(go())
    return out

def make_music(seconds):
    import numpy as np
    sr=44100; n=int(sr*seconds); t=np.arange(n)/sr
    sig=.018*np.sin(2*np.pi*220*t)+.012*np.sin(2*np.pi*277.18*t)+.008*np.sin(2*np.pi*329.63*t)
    fade=np.minimum(1,np.minimum(t,2))*np.minimum(1,(seconds-t)/2)
    sig*=np.clip(fade,0,1)
    out=tempfile.NamedTemporaryFile(delete=False,suffix=".wav").name
    with wave.open(out,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((sig*32767).astype(np.int16).tobytes())
    return out

def stamp(sec):
    ms=int(round((sec-int(sec))*1000)); s=int(sec)
    if ms>=1000: s+=1; ms-=1000
    return f"00:{s//60:02d}:{s%60:02d},{ms:03d}"


def add_brand_to_image(im, brand):
    # Exact deterministic branding on the source frame. The AI is NOT asked to spell the brand.
    from PIL import ImageDraw, ImageFont
    im=im.convert("RGBA")
    draw=ImageDraw.Draw(im)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(18, im.width//34))
    except Exception:
        font=ImageFont.load_default()
    text=(brand or "VAIBHAV").strip() or "VAIBHAV"
    box=draw.textbbox((0,0),text,font=font,stroke_width=2)
    tw,th=box[2]-box[0],box[3]-box[1]
    x=(im.width-tw)//2
    y=int(im.height*0.67)
    pad=9
    draw.rounded_rectangle((x-pad,y-pad,x+tw+pad,y+th+pad),radius=10,fill=(0,0,0,105))
    draw.text((x,y),text,font=font,fill=(255,255,255,238),stroke_width=2,stroke_fill=(0,0,0,170))
    return im

def ai_motion(t, image, prompt, duration):
    # Hugging Face Inference Providers expose image_to_video. Provider availability/cost depends on routing.
    c=get_client(t)
    frames=max(25,min(49,int(duration*5)))
    return c.image_to_video(
        image=image,
        model="Wan-AI/Wan2.1-I2V-14B-720P",
        prompt=prompt + ", natural motion, cinematic camera movement, stable anatomy, consistent character, realistic physics, no text, no watermark",
        negative_prompt="flicker, warping, deformed face, extra limbs, duplicated objects, text, logo, watermark",
        num_frames=frames,
        num_inference_steps=20,
    )

def brand_video(input_video, brand, output_video):
    ff="ffmpeg"
    safe=(brand or "VAIBHAV").replace("\\","").replace("'","").replace(":"," ")
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    vf=f"drawtext=fontfile={font}:text='{safe}':x=w-tw-24:y=h-th-28:fontsize=34:fontcolor=white@0.88:borderw=2:bordercolor=black@0.65"
    subprocess.run(
        [ff,"-y","-i",str(input_video),"-vf",vf,"-c:v","libx264","-preset","veryfast","-c:a","copy",str(output_video)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
    )

def render_motion_clips(clips,narr,lang,total,music_on,brand):
    ff="ffmpeg"
    work=Path(tempfile.mkdtemp(prefix="av10_motion_render_"))
    per=total/len(clips)
    voiced=[]
    for i,(clip,txt) in enumerate(zip(clips,narr)):
        ap=make_voice(txt,lang)
        out=work/f"voice_{i}.mp4"
        subprocess.run(
            [ff,"-y","-i",str(clip),"-i",ap,"-map","0:v:0","-map","1:a:0","-t",str(per),
             "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(out)],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
        )
        voiced.append(out)
    concat=work/"concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in voiced),encoding="utf-8")
    joined=work/"joined.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    mixed=joined
    if music_on:
        bed=make_music(total)
        mixed=work/"mixed.mp4"
        subprocess.run(
            [ff,"-y","-i",str(joined),"-i",bed,
             "-filter_complex","[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
             "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(mixed)],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
        )
    final=work/"final.mp4"
    brand_video(mixed,brand,final)
    return final

def render(images,narr,lang,total,aspect,res,captions,music_on):
    ff="ffmpeg"; work=Path(tempfile.mkdtemp(prefix="av9_"))
    if aspect=="9:16": W,H=(720,1280) if res=="720p" else (1080,1920)
    elif aspect=="1:1": W=H=720 if res=="720p" else 1080
    else: W,H=(1280,720) if res=="720p" else (1920,1080)
    per=total/len(images); clips=[]
    for i,(im,txt) in enumerate(zip(images,narr)):
        ip=work/f"scene_{i}.png"; im.save(ip)
        ap=make_voice(txt,lang)
        cp=work/f"clip_{i}.mp4"
        vf=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0006,1.05)':d=125:s={W}x{H}:fps=25"
        subprocess.run([ff,"-y","-loop","1","-i",str(ip),"-i",ap,"-t",str(per),
                        "-vf",vf,"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast",
                        "-pix_fmt","yuv420p","-c:a","aac","-shortest",str(cp)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        clips.append(cp)
    concat=work/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips))
    joined=work/"joined.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    srt=work/"captions.srt"; t=0; rows=[]
    for i,txt in enumerate(narr):
        e=min(total,t+per)
        rows.append(f"{i+1}\n{stamp(t)} --> {stamp(e)}\n{txt}\n\n"); t=e
    srt.write_text("".join(rows),encoding="utf-8")
    base=work/"captioned.mp4"
    if captions:
        # Noto Sans Devanagari is installed by packages.txt; force libass to use it.
        style="FontName=Noto Sans Devanagari,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=55"
        subprocess.run([ff,"-y","-i",str(joined),"-vf",f"subtitles={srt.as_posix()}:force_style='{style}'",
                        "-c:v","libx264","-preset","veryfast","-c:a","copy",str(base)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        base=joined
    final=work/"final.mp4"
    if music_on:
        bed=make_music(total)
        subprocess.run([ff,"-y","-i",str(base),"-i",bed,
                        "-filter_complex","[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
                        "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(final)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        final=base
    return final,srt

a,b=st.columns([1.25,.75])
with a:
    prompt=st.text_area("✍️ Prompt / Story idea",height=150,placeholder="एक छोटी प्रेरणादायी कथा...")
with b:
    lang=st.selectbox("🗣️ Language",["Marathi","Hindi","English","Hinglish"])
    scenes=st.selectbox("🎞️ Scenes",[2,3,4,5,6],index=0)
    duration=st.selectbox("⏱️ Duration (sec)",[12,15,20,30,45,60],index=1)
    aspect=st.selectbox("📐 Format",["9:16","16:9","1:1"],index=0)
    resolution=st.selectbox("📺 Output",["720p","1080p"],index=0)
    engine=st.selectbox("🎥 Video Engine",["AI Motion","Cinematic Fallback"],index=0)
    brand=st.text_input("🏷️ Branding","VAIBHAV")
    music=st.checkbox("🎵 Background music",True)

if st.button("🚀 GENERATE FINAL VIDEO",type="primary",use_container_width=True):
    if not token.strip():
        st.error("Enter your Hugging Face Access Token in the left sidebar first."); st.stop()
    if not prompt.strip():
        st.error("Enter a prompt first."); st.stop()
    try:
        with st.status("Creating final video...",expanded=True) as status:
            st.write("🧠 Planning story and characters...")
            story,mode=plan_story(token,prompt,lang,scenes)
            if mode=="Fallback":
                st.info("AI planner unavailable; deterministic story fallback is being used.")
            images=[]; narr=[]
            for i,s in enumerate(story["scenes"],1):
                st.write(f"🎨 Creating character-consistent visual {i}/{scenes}...")
                visual_prompt = s["visual_prompt"] + ", consistent recurring character, clean outfit, exact visible brand word VAIBHAV on clothing"
                im=make_image(token,visual_prompt)
                im=add_brand_to_image(im,brand)
                images.append(im)
                narr.append(s["narration"])

            if engine=="AI Motion":
                st.write("🎥 Generating real AI motion clips...")
                try:
                    clips=[]
                    clip_seconds=max(4,min(8,duration/scenes))
                    for i,(im,s) in enumerate(zip(images,story["scenes"]),1):
                        st.write(f"🎥 AI Motion {i}/{scenes}...")
                        raw=ai_motion(token,im,s["visual_prompt"],clip_seconds)
                        cp=Path(tempfile.mkdtemp(prefix="av10_clip_"))/f"scene_{i}.mp4"
                        cp.write_bytes(raw)
                        clips.append(cp)
                    st.write("🎙️ Generating voice...")
                    st.write("🎵 Mixing background music...")
                    st.write("🏷️ Applying exact VAIBHAV branding...")
                    video=render_motion_clips(clips,narr,lang,duration,music,brand)
                except Exception as motion_error:
                    st.warning("AI Motion provider is unavailable or requires paid provider credits. Falling back to cinematic motion.")
                    st.caption(str(motion_error))
                    st.write("🎬 Building cinematic fallback...")
                    video,srt=render(images,narr,lang,duration,aspect,resolution,False,music)
                    branded=Path(tempfile.mkdtemp(prefix="av10_brand_"))/"branded.mp4"
                    brand_video(video,brand,branded)
                    video=branded
            else:
                st.write("🎬 Building cinematic motion...")
                st.write("🎙️ Generating voice...")
                st.write("🎵 Mixing background music...")
                video,srt=render(images,narr,lang,duration,aspect,resolution,False,music)
                branded=Path(tempfile.mkdtemp(prefix="av10_brand_"))/"branded.mp4"
                brand_video(video,brand,branded)
                video=branded

            status.update(label="✅ FINAL VIDEO READY",state="complete")

        st.success("✅ Final video ready — visuals + voice + music + VAIBHAV branding. Captions are OFF.")
        st.video(str(video))
        with open(video,"rb") as f:
            st.download_button("⬇️ Download FINAL MP4",f,"VAIBHAV_FINAL_VIDEO.mp4","video/mp4",use_container_width=True)
        with st.expander("📋 Storyboard"):
            st.json(story)
    except Exception as e:
        st.error(f"Generation error: {e}")
        st.info("For the first test use 2 scenes / 15 sec / 720p. If AI Motion is unavailable, select Cinematic Fallback.")


st.markdown("---")
st.caption("V10 FINAL: VAIBHAV branding is automatic. Captions are OFF. AI Motion uses Hugging Face Inference Providers when available; provider video generation may require paid credits.")
