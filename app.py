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
    st.error("엔진 설치 중... 잠시만 기다린 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 프로 커스텀", page_icon="✨", layout="wide")

# --- 사이드바: 편집 컨트롤러 ---
st.sidebar.header("🎬 마스터 편집 도구")
target_total_duration = st.sidebar.number_input("⏱️ 목표 전체 영상 길이(초)", 5, 120, 20)
logo_duration = st.sidebar.slider("🖼️ 엔딩 로고 노출 시간(초)", 2.0, 5.0, 3.5)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 개별 이미지 시간 설정")

# 파일 업로드 (메인 화면)
st.title("☔ 비요일 숏폼 제작소 [BLUR EDITION]")
files = st.file_uploader("1. 사진/영상 파일을 모두 업로드하세요 (블러 배경이 자동 적용됩니다)", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

special_durations = {}

if files:
    img_names = [f.name for f in files if not f.name.lower().endswith(('.mp4', '.mov'))]
    if img_names:
        selected_imgs = st.sidebar.multiselect("길이를 다르게 할 이미지 선택", img_names)
        for name in selected_imgs:
            special_durations[name] = st.sidebar.slider(f"'{name}' 재생 시간(초)", 0.5, 10.0, 4.0)
    else:
        st.sidebar.write("선택할 수 있는 이미지가 없습니다.")
else:
    st.sidebar.info("파일을 업로드하면 개별 시간 설정 메뉴가 나타납니다.")

st.sidebar.markdown("---")
subtitle_y_pos = st.sidebar.slider("자막 높이 조절", 100, 500, 250)

# --- 처리 로직 ---
TARGET_W, TARGET_H = 1080, 1920

def create_subtitle_image(text, font_path, font_size=60, y_pos=250):
    img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else PIL.ImageFont.load_default()
    except: font = PIL.ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - y_pos
    padding = 30
    draw.rectangle([tx - padding, ty - padding, tx + tw + padding, ty + th + padding], fill=(0, 0, 0, 160))
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
    img.save(temp_p)
    return temp_p

def apply_blur_bg(pil_img):
    """이미지에 블러 배경을 입힙니다."""
    # 1. 배경용: 크게 확대해서 흐리게 만들기
    bg = pil_img.resize((TARGET_W, TARGET_H), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=50))
    # 2. 전경용: 비율 유지하며 맞추기
    fg = PIL.ImageOps.contain(pil_img, (TARGET_W, TARGET_H))
    # 3. 합치기
    bg.paste(fg, ((TARGET_W-fg.size[0])//2, (TARGET_H-fg.size[1])//2))
    return bg

def process_source(file, duration=None):
    ext = os.path.splitext(file.name)[1].lower()
    try:
        if ext in ['.mp4', '.mov']:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
                t.write(file.read())
                raw_clip = VideoFileClip(t.name).without_audio()
                
                # 영상용 블러 배경 만들기 (첫 프레임을 블러 배경으로 사용)
                first_frame = raw_clip.get_frame(0)
                bg_img = PIL.Image.fromarray(first_frame)
                bg_with_blur = apply_blur_bg(bg_img)
                
                temp_bg_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                bg_with_blur.save(temp_bg_p)
                
                # 배경 클립과 전경 영상 합성
                bg_clip = ImageClip(temp_bg_p).with_duration(raw_clip.duration)
                fg_clip = raw_clip.resized(width=TARGET_W) if raw_clip.w > raw_clip.h else raw_clip.resized(height=TARGET_H)
                
                final_clip = CompositeVideoClip([bg_clip, fg_clip.with_position("center")])
                return final_clip
        else:
            img_data = file.read()
            img = PIL.Image.open(io.BytesIO(img_data)).convert("RGB")
            processed_img = apply_blur_bg(img)
            
            temp_img_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            processed_img.save(temp_img_p)
            return ImageClip(temp_img_p).with_duration(duration)
    except Exception as e:
        st.error(f"파일 처리 중 오류: {e}")
        return None

# 메인 UI
subtitle_text = st.text_input("자막 입력", "비요일: 당신의 하루를 지켜줄 양우산")
logo = st.file_uploader("2. 브랜드 로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

if st.button("🚀 블러 배경으로 영상 제작 시작"):
    if files and logo:
        with st.spinner('블랙 바를 제거하고 감성적인 배경을 입히는 중...'):
            try:
                # 1. 동영상 먼저 처리하여 시간 계산
                video_clips = {}
                image_files = []
                total_video_time = 0
                
                for f in files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        v = process_source(f)
                        video_clips[f.name] = v
                        total_video_time += v.duration
                    else:
                        image_files.append(f)
                
                # 2. 이미지 시간 계산
                total_special_time = sum(special_durations.values())
                normal_imgs = [f for f in image_files if f.name not in special_durations]
                
                remaining_time = target_total_duration - total_video_time - logo_duration - total_special_time
                base_img_duration = remaining_time / len(normal_imgs) if len(normal_imgs) > 0 else 0
                
                # 3. 클립 조립
                final_clips = []
                overlap = 0.5
                
                for f in files:
                    if f.name in video_clips:
                        c = video_clips[f.name]
                    else:
                        this_dur = special_durations.get(f.name, base_img_duration)
                        c = process_source(f, duration=this_dur)
                    
                    if len(final_clips) == 0:
                        c = c.with_effects([vfx.CrossFadeOut(overlap)])
                    else:
                        c = c.with_effects([vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)])
                    final_clips.append(c)
                
                # 로고 (로고도 블러 배경 적용)
                l_clip = process_source(logo, duration=logo_duration).with_effects([
                    vfx.CrossFadeIn(overlap), vfx.Resize(lambda t: 1 + 0.02 * t)
                ])
                final_clips.append(l_clip)
                
                video_only = concatenate_videoclips(final_clips, method="compose", padding=-overlap)
                
                if subtitle_text:
                    sub_p = create_subtitle_image(subtitle_text, "font.otf", y_pos=subtitle_y_pos)
                    sub_clip = ImageClip(sub_p).with_duration(video_only.duration).with_fps(24)
                    final_video = CompositeVideoClip([video_only, sub_clip])
                else:
                    final_video = video_only
                
                if bgm:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                        mt.write(bgm.read())
                        audio = AudioFileClip(mt.name).with_duration(final_video.duration)
                        audio = audio.with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                        final_video = final_video.with_audio(audio)
                
                output = "biyoil_blur_final.mp4"
                final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
                st.video(output)
                st.success(f"🎉 완성! 블랙 바 없이 총 {round(final_video.duration, 1)}초로 제작되었습니다.")
            except Exception as e:
                st.error(f"제작 오류: {e}")
    else:
        st.warning("파일을 모두 올려주세요.")
