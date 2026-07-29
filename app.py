import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
import io

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

# --- 유틸리티 함수 ---
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
    bg = pil_img.resize((TARGET_W, TARGET_H), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=50))
    fg = PIL.ImageOps.contain(pil_img, (TARGET_W, TARGET_H))
    bg.paste(fg, ((TARGET_W-fg.size[0])//2, (TARGET_H-fg.size[1])//2))
    return bg

def process_source_to_clip(file, duration=2.0):
    ext = os.path.splitext(file.name)[1].lower()
    if ext in ['.mp4', '.mov']:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
            t.write(file.getvalue())
            raw = VideoFileClip(t.name).without_audio()
            bg_f = PIL.Image.fromarray(raw.get_frame(0))
            bg_blur = apply_blur_bg(bg_f)
            temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            bg_blur.save(temp_p)
            bg_c = ImageClip(temp_p).with_duration(raw.duration)
            fg_c = raw.resized(width=TARGET_W) if raw.w > raw.h else raw.resized(height=TARGET_H)
            return CompositeVideoClip([bg_c, fg_c.with_position("center")])
    else:
        img = PIL.Image.open(io.BytesIO(file.getvalue())).convert("RGB")
        processed = apply_blur_bg(img)
        temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        processed.save(temp_p)
        return ImageClip(temp_p).with_duration(duration)

# --- 사이드바: 전역 설정 ---
st.sidebar.header("🎬 전역 편집 설정")
target_total = st.sidebar.number_input("⏱️ 목표 전체 길이(초)", 5, 120, 20)
logo_dur = st.sidebar.slider("🖼️ 로고 노출 시간(초)", 2.0, 5.0, 3.5)
sub_style = st.sidebar.selectbox("🎨 자막 디자인", ["Classic Bar (검정바)", "Modern Shadow (그림자)", "Elegant Border (테두리)"])
sub_y = st.sidebar.slider("📏 자막 높이", 100, 600, 250)

# --- 메인 화면 ---
st.title("☔ 비요일 숏폼 스튜디오 [ULTIMATE]")

uploaded_files = st.file_uploader("1. 사진/영상 파일을 모두 업로드하세요", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

if 'subs' not in st.session_state: st.session_state.subs = {}
if 'durs' not in st.session_state: st.session_state.durs = {}

if uploaded_files:
    tab_edit, tab_preview = st.tabs(["📝 장면별 상세 설정", "🖼️ 실시간 프리뷰"])
    
    with tab_edit:
        st.subheader("개별 자막 및 시간 지정")
        cols = st.columns(2)
        for i, f in enumerate(uploaded_files):
            with cols[i % 2]:
                st.write(f"**장면 {i+1}: {f.name}**")
                st.session_state.subs[f.name] = st.text_input(f"자막 입력", key=f"s_{f.name}", value=st.session_state.subs.get(f.name, ""))
                if not f.name.lower().endswith(('.mp4', '.mov')):
                    if st.checkbox("시간 개별 지정", key=f"c_{f.name}"):
                        st.session_state.durs[f.name] = st.slider("재생 시간", 0.5, 10.0, st.session_state.durs.get(f.name, 4.0), key=f"d_{f.name}")
                    elif f.name in st.session_state.durs:
                        del st.session_state.durs[f.name]

    with tab_preview:
        st.subheader("현재 설정 미리보기")
        p_cols = st.columns(3)
        for i, f in enumerate(uploaded_files):
            with p_cols[i % 3]:
                if f.name.lower().endswith(('.mp4', '.mov')):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                        t.write(f.getvalue())
                        raw = VideoFileClip(t.name)
                        frame = PIL.Image.fromarray(raw.get_frame(0))
                else:
                    frame = PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                
                prev_img = apply_blur_bg(frame)
                txt = st.session_state.subs.get(f.name, "")
                if txt:
                    sub_layer = create_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y)
                    prev_img = PIL.Image.alpha_composite(prev_img.convert("RGBA"), sub_layer)
                st.image(prev_img, caption=f"{i+1}. {f.name}", use_container_width=True)

    st.markdown("---")
    logo = st.file_uploader("2. 브랜드 로고 업로드", type=['jpg','png'])
    bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

    if st.button("🚀 최종 고화질 영상 제작 시작"):
        if not logo:
            st.error("로고 파일을 올려주세요!")
        else:
            with st.spinner('영상을 정밀하게 굽는 중입니다...'):
                try:
                    # 1. 시간 계산 로직 (에러 수정: image_files 이름 통일)
                    v_clips_dict = {}
                    image_files = [] # 리스트 이름 통일
                    total_v_time = 0
                    for f in uploaded_files:
                        if f.name.lower().endswith(('.mp4', '.mov')):
                            vc = process_source_to_clip(f)
                            v_clips_dict[f.name] = vc
                            total_v_time += vc.duration
                        else:
                            image_files.append(f) # 통일된 이름 사용

                    spec_time = sum(st.session_state.durs.values())
                    norm_imgs = [f for f in image_files if f.name not in st.session_state.durs]
                    
                    # 겹치는 시간(overlap) 보정 계산
                    overlap = 0.5
                    num_clips = len(uploaded_files) + 1
                    req_total = target_total + (num_clips - 1) * overlap
                    
                    remaining = req_total - total_v_time - logo_dur - spec_time
                    base_dur = remaining / len(norm_imgs) if len(norm_imgs) > 0 else 0
                    
                    if remaining < 0 and len(norm_imgs) > 0:
                        st.error("설정한 전체 길이가 너무 짧습니다. 목표 길이를 늘려주세요.")
                        st.stop()

                    # 2. 합성
                    final_clips = []
                    for f in uploaded_files:
                        if f.name in v_clips_dict:
                            c = v_clips_dict[f.name]
                        else:
                            d = st.session_state.durs.get(f.name, base_dur)
                            c = process_source_to_clip(f, duration=d)
                        
                        txt = st.session_state.subs.get(f.name, "")
                        if txt:
                            sub_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            create_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y).save(sub_p)
                            c = CompositeVideoClip([c, ImageClip(sub_p).with_duration(c.duration).with_fps(24)])
                        
                        eff = [vfx.CrossFadeOut(overlap)] if len(final_clips)==0 else [vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)]
                        final_clips.append(c.with_fps(24).with_effects(eff))

                    # 로고
                    l_c = process_source_to_clip(logo, duration=logo_dur).with_effects([
                        vfx.CrossFadeIn(overlap), vfx.Resize(lambda t: 1 + 0.02 * t)
                    ])
                    final_clips.append(l_c.with_fps(24))

                    res_v = concatenate_videoclips(final_clips, method="compose", padding=-overlap)
                    if bgm:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                            mt.write(bgm.read())
                            audio = AudioFileClip(mt.name).with_duration(res_v.duration).with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                            res_v = res_v.with_audio(audio)
                    
                    out_path = "biyoil_final_ultimate.mp4"
                    res_v.write_videofile(out_path, fps=24, codec="libx264")
                    st.video(out_path)
                    st.success("🎉 드디어 완벽하게 완성되었습니다!")
                except Exception as e: st.error(f"오류: {e}")
else:
    st.info("💡 사진이나 영상을 먼저 올려주세요! (Pretendard 폰트 자막과 블러 배경이 적용됩니다)")
