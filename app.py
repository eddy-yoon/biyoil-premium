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
    st.error("엔진 설치 마무리 중... 1~2분만 기다린 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 프로 커스텀", page_icon="✨", layout="wide")

# --- 사이드바 ---
st.sidebar.header("🎬 편집 컨트롤러")
target_total_duration = st.sidebar.number_input("목표 전체 영상 길이(초)", 5, 120, 20)
logo_duration = st.sidebar.slider("엔딩 로고 노출 시간(초)", 2.0, 5.0, 3.5)
subtitle_y_pos = st.sidebar.slider("자막 높이 조절", 100, 500, 250)

st.title("☔ 비요일 숏폼 제작소 [PREMIUM CUSTOM]")

TARGET_W, TARGET_H = 1080, 1920

def create_subtitle_image(text, font_path, font_size=60, y_pos=250):
    img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try:
        font = PIL.ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else PIL.ImageFont.load_default()
    except:
        font = PIL.ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - y_pos
    padding = 30
    draw.rectangle([tx - padding, ty - padding, tx + tw + padding, ty + th + padding], fill=(0, 0, 0, 160))
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
    img.save(temp_p)
    return temp_p

def process_video(file):
    ext = os.path.splitext(file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
        t.write(file.read())
        clip = VideoFileClip(t.name).without_audio().resized(width=1080)
        if clip.h > 1920:
            clip = clip.cropped(y_center=clip.h/2, height=1920)
        elif clip.h < 1920:
            top_m = (1920 - clip.h) // 2
            bottom_m = 1920 - clip.h - top_m
            clip = clip.with_effects([vfx.Margin(top=top_m, bottom=bottom_m, color=(0,0,0))])
        return clip

def process_image(file, duration):
    img_data = file.read()
    img = PIL.Image.open(io.BytesIO(img_data)).convert("RGB")
    bg = img.resize((1080, 1920), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=40))
    fg = PIL.ImageOps.contain(img, (1080, 1920))
    bg.paste(fg, ((1080-fg.size[0])//2, (1920-fg.size[1])//2))
    temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
    bg.save(temp_p)
    return ImageClip(temp_p).with_duration(duration)

files = st.file_uploader("사진/영상 업로드", accept_multiple_files=True, type=['jpg','png','mp4','mov'])
subtitle_text = st.text_input("자막 입력", "비요일: 당신의 하루를 지켜줄 양우산")
logo = st.file_uploader("로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("배경음악(MP3)", type=['mp3'])

if st.button("🚀 커스텀 영상 제작 시작"):
    if files and logo:
        with st.spinner('영상의 모든 분량을 계산하여 제작 중입니다...'):
            try:
                # 1. 파일 분류 및 동영상 원본 시간 계산
                video_clips = []
                image_files = []
                total_video_time = 0
                
                for f in files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        v_clip = process_video(f)
                        video_clips.append(v_clip)
                        total_video_time += v_clip.duration
                    else:
                        image_files.append(f)
                
                # 2. 이미지당 배분할 시간 계산
                remaining_time = target_total_duration - total_video_time - logo_duration
                
                if remaining_time <= 0:
                    st.error(f"동영상 합계({round(total_video_time, 1)}초)와 로고 시간이 설정한 전체 시간보다 깁니다. 목표 길이를 늘려주세요.")
                    st.stop()
                
                img_duration = remaining_time / len(image_files) if image_files else 0
                
                # 3. 모든 클립 합치기 리스트 생성
                final_clip_list = []
                
                # 업로드 순서를 유지하기 위해 다시 루프 (동영상은 이미 생성된 clip 사용)
                v_idx = 0
                for f in files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        c = video_clips[v_idx]
                        v_idx += 1
                    else:
                        c = process_image(f, img_duration)
                    
                    # 페이드 효과 (첫장면 블랙방지 로직 포함)
                    if len(final_clip_list) == 0:
                        c = c.with_effects([vfx.CrossFadeOut(0.5)])
                    else:
                        c = c.with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)])
                    final_clip_list.append(c)
                
                # 로고 추가
                l_clip = process_image(logo, logo_duration).with_effects([
                    vfx.CrossFadeIn(0.5), vfx.Resize(lambda t: 1 + 0.02 * t)
                ])
                final_clip_list.append(l_clip)
                
                # 4. 최종 합성
                video_only = concatenate_videoclips(final_clip_list, method="compose", padding=-0.5)
                
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
                
                output = "biyoil_final_sync.mp4"
                final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
                st.video(output)
                st.success(f"🎉 성공! 동영상을 모두 살려 총 {round(final_video.duration, 1)}초로 제작되었습니다.")
            except Exception as e:
                st.error(f"제작 중 오류 발생: {e}")
    else:
        st.warning("파일을 올려주세요.")
