import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
import io
import gc # 메모리 관리를 위한 도구

# 1. 환경 설정 및 패치
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.Resampling = PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

try:
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, afx, CompositeVideoClip
except ImportError:
    st.error("엔진 설치 중... 1분만 기다린 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 얼티밋 스튜디오", page_icon="🎬", layout="wide")

TARGET_W, TARGET_H = 1080, 1920

def create_subtitle_img(text, style, font_path, font_size=70, y_pos=250):
    img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else PIL.ImageFont.load_default()
    except: font = PIL.ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - y_pos
    if style == "Classic Bar (검정바)":
        draw.rectangle([tx-30, ty-20, tx+tw+30, ty+th+20], fill=(0, 0, 0, 160))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    elif style == "Modern Shadow (그림자)":
        draw.text((tx+5, ty+5), text, font=font, fill=(0, 0, 0, 150))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    else: # Border
        for ox, oy in [(-3,-3),(3,3),(-3,3),(3,-3)]:
            draw.text((tx+ox, ty+oy), text, font=font, fill=(0, 0, 0, 200))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    return img

def apply_blur_bg(pil_img):
    # 메모리 절약을 위해 배경 이미지는 조금 작게 만든 뒤 확대
    bg = pil_img.resize((TARGET_W//2, TARGET_H//2), PIL.Image.Resampling.LANCZOS)
    bg = bg.filter(PIL.ImageFilter.GaussianBlur(radius=20))
    bg = bg.resize((TARGET_W, TARGET_H), PIL.Image.Resampling.LANCZOS)
    fg = PIL.ImageOps.contain(pil_img, (TARGET_W, TARGET_H))
    bg.paste(fg, ((TARGET_W-fg.size[0])//2, (TARGET_H-fg.size[1])//2))
    return bg

# --- 사이드바 및 UI ---
st.sidebar.header("🎬 전역 편집 설정")
target_total = st.sidebar.number_input("⏱️ 목표 전체 길이(초)", 5, 120, 20)
logo_dur = st.sidebar.slider("🖼️ 로고 노출 시간(초)", 2.0, 5.0, 3.5)
sub_style = st.sidebar.selectbox("🎨 자막 디자인", ["Classic Bar (검정바)", "Modern Shadow (그림자)", "Elegant Border (테두리)"])
sub_y = st.sidebar.slider("📏 자막 높이", 100, 600, 250)

st.title("☔ 비요일 숏폼 스튜디오 [ULTIMATE v2]")
uploaded_files = st.file_uploader("1. 사진/영상 업로드", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

if 'subs' not in st.session_state: st.session_state.subs = {}
if 'durs' not in st.session_state: st.session_state.durs = {}

if uploaded_files:
    tab_edit, tab_preview = st.tabs(["📝 장면별 상세 설정", "🖼️ 실시간 프리뷰"])
    
    with tab_edit:
        cols = st.columns(2)
        for i, f in enumerate(uploaded_files):
            with cols[i % 2]:
                st.write(f"**장면 {i+1}: {f.name}**")
                st.session_state.subs[f.name] = st.text_input(f"자막", key=f"s_{f.name}", value=st.session_state.subs.get(f.name, ""))
                if not f.name.lower().endswith(('.mp4', '.mov')):
                    if st.checkbox("시간 개별 지정", key=f"c_{f.name}"):
                        st.session_state.durs[f.name] = st.slider("재생 시간", 0.5, 10.0, st.session_state.durs.get(f.name, 4.0), key=f"d_{f.name}")
                    elif f.name in st.session_state.durs: del st.session_state.durs[f.name]

    with tab_preview:
        p_cols = st.columns(3)
        for i, f in enumerate(uploaded_files):
            with p_cols[i % 3]:
                if f.name.lower().endswith(('.mp4', '.mov')):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                        t.write(f.getvalue())
                        raw = VideoFileClip(t.name)
                        frame = PIL.Image.fromarray(raw.get_frame(0))
                        raw.close()
                else:
                    frame = PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                
                prev_img = apply_blur_bg(frame)
                txt = st.session_state.subs.get(f.name, "")
                if txt:
                    sub_layer = create_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y)
                    prev_img = PIL.Image.alpha_composite(prev_img.convert("RGBA"), sub_layer)
                st.image(prev_img, caption=f"{i+1}. {f.name}", use_container_width=True)

    st.markdown("---")
    logo = st.file_uploader("2. 로고 업로드", type=['jpg','png'])
    bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

    if st.button("🚀 최종 고화질 영상 제작 시작"):
        if not logo: st.error("로고를 올려주세요!")
        else:
            with st.spinner('서버 부하를 줄이며 조심스럽게 영상을 제작 중입니다...'):
                try:
                    final_clips = []
                    overlap = 0.5
                    
                    # 1. 시간 계산 및 비디오 클립 생성
                    v_clips_dict = {}
                    image_files = []
                    total_v_time = 0
                    for f in uploaded_files:
                        if f.name.lower().endswith(('.mp4', '.mov')):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                                t.write(f.getvalue())
                                vc = VideoFileClip(t.name).without_audio().resized(width=TARGET_W)
                                if vc.h > TARGET_H: vc = vc.cropped(y_center=vc.h/2, height=TARGET_H)
                                # 비디오 배경 처리
                                bg_f = PIL.Image.fromarray(vc.get_frame(0))
                                bg_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                                apply_blur_bg(bg_f).save(bg_p)
                                bg_c = ImageClip(bg_p).with_duration(vc.duration)
                                v_clips_dict[f.name] = CompositeVideoClip([bg_c, vc.with_position("center")])
                                total_v_time += vc.duration
                        else:
                            image_files.append(f)

                    # 이미지 배분 시간 계산
                    spec_time = sum(st.session_state.durs.values())
                    norm_imgs = [f for f in image_files if f.name not in st.session_state.durs]
                    num_clips = len(uploaded_files) + 1
                    req_total = target_total + (num_clips - 1) * overlap
                    base_dur = (req_total - total_v_time - logo_dur - spec_time) / len(norm_imgs) if norm_imgs else 0
                    
                    # 2. 클립 조립
                    for f in uploaded_files:
                        if f.name in v_clips_dict:
                            c = v_clips_dict[f.name]
                        else:
                            d = st.session_state.durs.get(f.name, base_dur)
                            img = apply_blur_bg(PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB"))
                            p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            img.save(p)
                            c = ImageClip(p).with_duration(d)
                        
                        txt = st.session_state.subs.get(f.name, "")
                        if txt:
                            sub_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            create_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y).save(sub_p)
                            sub_clip = ImageClip(sub_p).with_duration(c.duration).with_fps(24)
                            c = CompositeVideoClip([c, sub_clip])
                        
                        eff = [vfx.CrossFadeOut(overlap)] if len(final_clips)==0 else [vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)]
                        final_clips.append(c.with_fps(24).with_effects(eff))

                    # 로고 추가
                    l_img = apply_blur_bg(PIL.Image.open(io.BytesIO(logo.read())).convert("RGB"))
                    lp = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    l_img.save(lp)
                    final_clips.append(ImageClip(lp).with_duration(logo_dur).with_fps(24).with_effects([vfx.CrossFadeIn(overlap), vfx.Resize(lambda t: 1 + 0.02 * t)]))

                    # 3. 최종 합성 및 파일 쓰기 (메모리 절약 옵션 추가)
                    res_v = concatenate_videoclips(final_clips, method="compose", padding=-overlap)
                    if bgm:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                            mt.write(bgm.read())
                            audio = AudioFileClip(mt.name).with_duration(res_v.duration).with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                            res_v = res_v.with_audio(audio)
                    
                    res_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=1)
                    st.video("final.mp4")
                    st.success("🎉 드디어 성공!")
                    
                    # 메모리 비우기
                    res_v.close()
                    for c in final_clips: c.close()
                    gc.collect()

                except Exception as e: st.error(f"오류: {e}")
