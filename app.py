import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
import io

# 1. Pillow 패치
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.Resampling = PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

try:
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, afx, CompositeVideoClip
except ImportError:
    st.error("엔진 설치 중... 잠시 대기 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 편집 스튜디오", page_icon="🎬", layout="wide")

# --- 설정 및 규격 ---
TARGET_W, TARGET_H = 1080, 1920

def create_styled_subtitle_img(text, style, font_path, font_size=70, y_pos=250):
    """자막 이미지를 PIL 객체로 반환 (프리뷰용)"""
    img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else PIL.ImageFont.load_default()
    except: font = PIL.ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - y_pos
    
    padding = 30
    if style == "Classic Bar (검정바)":
        draw.rectangle([tx-padding, ty-padding, tx+tw+padding, ty+th+padding], fill=(0, 0, 0, 160))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    elif style == "Modern Shadow (그림자)":
        draw.text((tx+5, ty+5), text, font=font, fill=(0, 0, 0, 150))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    elif style == "Elegant Border (테두리)":
        stroke_w = 4
        for ox in range(-stroke_w, stroke_w+1):
            for oy in range(-stroke_w, stroke_w+1):
                draw.text((tx+ox, ty+oy), text, font=font, fill=(0, 0, 0, 200))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    return img

def apply_blur_bg(pil_img):
    """블러 배경 적용된 PIL 이미지 반환"""
    bg = pil_img.resize((TARGET_W, TARGET_H), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=50))
    fg = PIL.ImageOps.contain(pil_img, (TARGET_W, TARGET_H))
    bg.paste(fg, ((TARGET_W-fg.size[0])//2, (TARGET_H-fg.size[1])//2))
    return bg

# --- 사이드바 설정 ---
st.sidebar.header("🎬 전역 편집 설정")
target_total = st.sidebar.number_input("⏱️ 목표 전체 길이(초)", 5, 120, 20)
logo_dur = st.sidebar.slider("🖼️ 로고 노출 시간(초)", 2.0, 5.0, 3.5)
sub_style = st.sidebar.selectbox("🎨 자막 디자인 스타일", ["Classic Bar (검정바)", "Modern Shadow (그림자)", "Elegant Border (테두리)"])
sub_y = st.sidebar.slider("📏 자막 높이 조절", 100, 600, 250)

# --- 메인 화면 ---
st.title("☔ 비요일 숏폼 스튜디오 [PREVIEW MODE]")

uploaded_files = st.file_uploader("1. 사진/영상 파일을 업로드하세요", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

if uploaded_files:
    # 탭으로 화면 분할
    tab_edit, tab_preview = st.tabs(["📝 장면별 설정", "🖼️ 실시간 프리뷰"])
    
    clip_subtitles = {}
    special_durations = {}

    with tab_edit:
        st.write("각 장면의 자막과 시간을 입력하세요.")
        cols = st.columns(2)
        for i, f in enumerate(uploaded_files):
            with cols[i % 2]:
                st.info(f"📄 {f.name}")
                clip_subtitles[f.name] = st.text_input(f"자막 입력", key=f"sub_{f.name}")
                if not f.name.lower().endswith(('.mp4', '.mov')):
                    if st.checkbox("시간 개별 지정", key=f"chk_{f.name}"):
                        special_durations[f.name] = st.slider("재생 시간", 0.5, 10.0, 4.0, key=f"dur_{f.name}")

    with tab_preview:
        st.write("자막과 배경이 적용된 예상 모습입니다.")
        prev_cols = st.columns(3)
        for i, f in enumerate(uploaded_files):
            with prev_cols[i % 3]:
                # 이미지/영상 첫 프레임 가져오기
                try:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                            t.write(f.getvalue())
                            raw = VideoFileClip(t.name)
                            frame = PIL.Image.fromarray(raw.get_frame(0))
                    else:
                        frame = PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                    
                    # 블러 배경 적용
                    preview_img = apply_blur_bg(frame)
                    
                    # 자막 합성
                    txt = clip_subtitles.get(f.name, "")
                    if txt:
                        sub_layer = create_styled_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y)
                        preview_img = PIL.Image.alpha_composite(preview_img.convert("RGBA"), sub_layer)
                    
                    st.image(preview_img, caption=f"장면 {i+1} 미리보기", use_container_width=True)
                except:
                    st.error(f"{f.name} 미리보기 실패")

    st.markdown("---")
    logo = st.file_uploader("2. 브랜드 로고 업로드", type=['jpg','png'])
    bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

    if st.button("🚀 최종 영상 제작 시작"):
        # (기존 제작 로직 동일하게 유지...)
        with st.spinner('영상을 정밀하게 합성 중입니다...'):
            try:
                # 1. 시간 계산
                v_clips_dict = {}
                img_files = []
                total_v_time = 0
                for f in uploaded_files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                            t.write(f.read())
                            raw = VideoFileClip(t.name).without_audio()
                            # 블러 배경 처리
                            bg_img = PIL.Image.fromarray(raw.get_frame(0))
                            bg_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            apply_blur_bg(bg_img).save(bg_p)
                            bg_c = ImageClip(bg_p).with_duration(raw.duration)
                            fg_c = raw.resized(width=TARGET_W) if raw.w > raw.h else raw.resized(height=TARGET_H)
                            v_clips_dict[f.name] = CompositeVideoClip([bg_c, fg_c.with_position("center")])
                            total_v_time += raw.duration
                    else:
                        img_files.append(f)
                
                total_spec = sum(special_durations.values())
                norm_imgs = [f for f in img_files if f.name not in special_durations]
                base_dur = (target_total - total_v_time - logo_dur - total_spec) / len(norm_imgs) if norm_imgs else 0
                
                # 2. 합성
                final_clips = []
                overlap = 0.5
                for f in uploaded_files:
                    if f.name in v_clips_dict:
                        c = v_clips_dict[f.name]
                    else:
                        d = special_durations.get(f.name, base_dur)
                        img = PIL.Image.open(io.BytesIO(f.read())).convert("RGB")
                        p_img = apply_blur_bg(img)
                        p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                        p_img.save(p)
                        c = ImageClip(p).with_duration(d)
                    
                    txt = clip_subtitles.get(f.name, "")
                    if txt:
                        sub_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                        create_styled_subtitle_img(txt, sub_style, "font.otf", y_pos=sub_y).save(sub_p)
                        sub_c = ImageClip(sub_p).with_duration(c.duration).with_fps(24)
                        c = CompositeVideoClip([c, sub_c])
                    
                    c = c.with_fps(24).with_effects([vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)])
                    final_clips.append(c)
                
                # 로고 추가
                if logo:
                    l_img = PIL.Image.open(io.BytesIO(logo.read())).convert("RGB")
                    lp = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    apply_blur_bg(l_img).save(lp)
                    l_c = ImageClip(lp).with_duration(logo_dur).with_fps(24).with_effects([vfx.CrossFadeIn(overlap), vfx.Resize(lambda t: 1 + 0.02 * t)])
                    final_clips.append(l_c)

                final_v = concatenate_videoclips(final_clips, method="compose", padding=-overlap)
                
                if bgm:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                        mt.write(bgm.read())
                        audio = AudioFileClip(mt.name).with_duration(final_v.duration).with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                        final_v = final_v.with_audio(audio)
                
                out = "biyoil_preview_final.mp4"
                final_v.write_videofile(out, fps=24, codec="libx264")
                st.video(out)
                st.success("완성!")
            except Exception as e:
                st.error(f"오류: {e}")
