import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
import io

# 1. Pillow 최신 버전 에러 방지 패치
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

# --- 사이드바: 편집 컨트롤러 ---
st.sidebar.header("🎬 편집 컨트롤러")
edit_mode = st.sidebar.radio("편집 기준 선택", ["사진당 시간(속도) 조절", "전체 영상 길이 맞춤"])

if edit_mode == "사진당 시간(속도) 조절":
    duration_per_clip = st.sidebar.slider("사진 1장당 재생 시간(초)", 0.5, 5.0, 2.0, step=0.1)
else:
    target_total_duration = st.sidebar.number_input("목표 전체 영상 길이(초)", 5, 60, 20)

logo_duration = st.sidebar.slider("엔딩 로고 노출 시간(초)", 2.0, 5.0, 3.5)
subtitle_y_pos = st.sidebar.slider("자막 높이 조절 (밑에서부터)", 100, 500, 250)

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

def process_premium(file, clip_duration):
    ext = os.path.splitext(file.name)[1].lower()
    try:
        if ext in ['.mp4', '.mov']:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
                t.write(file.read())
                clip = VideoFileClip(t.name).without_audio().resized(width=1080)
                
                # [시간 보정]: 동영상도 설정한 시간에 맞게 자르거나 조절
                if clip.duration > clip_duration:
                    clip = clip.subclipped(0, clip_duration)
                else:
                    clip = clip.with_duration(clip_duration)
                
                if clip.h > 1920:
                    clip = clip.cropped(y_center=clip.h/2, height=1920)
                elif clip.h < 1920:
                    top_m = (1920 - clip.h) // 2
                    bottom_m = 1920 - clip.h - top_m
                    # [에러 수정]: vfx.Margin 사용
                    clip = clip.with_effects([vfx.Margin(top=top_m, bottom=bottom_m, color=(0,0,0))])
                return clip
        else:
            img_data = file.read()
            img = PIL.Image.open(io.BytesIO(img_data)).convert("RGB")
            bg = img.resize((1080, 1920), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=40))
            fg = PIL.ImageOps.contain(img, (1080, 1920))
            bg.paste(fg, ((1080-fg.size[0])//2, (1920-fg.size[1])//2))
            
            temp_img_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            bg.save(temp_img_p)
            return ImageClip(temp_img_p).with_duration(clip_duration)
    except Exception as e:
        st.error(f"'{file.name}' 처리 중 오류: {e}")
        return None

files = st.file_uploader("사진/영상 업로드", accept_multiple_files=True, type=['jpg','png','mp4','mov'])
subtitle_text = st.text_input("자막 입력", "비요일: 당신의 하루를 지켜줄 양우산")
logo = st.file_uploader("로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("배경음악(MP3)", type=['mp3'])

if st.button("🚀 커스텀 영상 제작 시작"):
    if files and logo:
        with st.spinner('영상을 굽는 중...'):
            try:
                num_files = len(files)
                # 전체 길이에 맞게 1개 파일당 시간 자동 계산
                if edit_mode == "전체 영상 길이 맞춤":
                    actual_duration = max(0.5, (target_total_duration - logo_duration) / num_files)
                else:
                    actual_duration = duration_per_clip

                all_clips = []
                for i, f in enumerate(files):
                    c = process_premium(f, actual_duration)
                    if c:
                        if i == 0:
                            c = c.with_effects([vfx.CrossFadeOut(0.5)])
                        else:
                            c = c.with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)])
                        all_clips.append(c)
                
                l_clip = process_premium(logo, logo_duration)
                if l_clip:
                    l_clip = l_clip.with_effects([vfx.CrossFadeIn(0.5), vfx.Resize(lambda t: 1 + 0.02 * t)])
                    all_clips.append(l_clip)
                
                video_only = concatenate_videoclips(all_clips, method="compose", padding=-0.5)
                
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
                
                output = "biyoil_perfect_20s.mp4"
                final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
                st.video(output)
                st.success(f"🎉 성공! 총 길이 {round(final_video.duration, 1)}초 영상을 확인하세요.")
            except Exception as e:
                st.error(f"치명적 에러: {e}")
    else:
        st.warning("파일을 모두 올려주세요.")
