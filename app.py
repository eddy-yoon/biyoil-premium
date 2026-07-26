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
    st.error("엔진 설치 중... 1~2분만 기다린 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 프로 커스텀", page_icon="✨", layout="wide")

# --- 메인 화면 상단 (파일 업로드 먼저) ---
st.title("☔ 비요일 숏폼 제작소 [FREE SELECT]")

files = st.file_uploader("1. 먼저 사진/영상 파일을 모두 업로드하세요", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

# --- 사이드바: 파일이 업로드된 후에 설정 창 노출 ---
st.sidebar.header("🎬 편집 컨트롤러")
target_total_duration = st.sidebar.number_input("목표 전체 영상 길이(초)", 5, 120, 20)
logo_duration = st.sidebar.slider("엔딩 로고 노출 시간(초)", 2.0, 5.0, 3.5)

special_files = []
special_img_duration = 2.0

if files:
    # 이미지 파일 이름만 추출
    img_names = [f.name for f in files if not f.name.lower().endswith(('.mp4', '.mov'))]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📍 특정 이미지 길이 지정")
    special_files = st.sidebar.multiselect("길이를 다르게 할 이미지 선택", img_names)
    if special_files:
        special_img_duration = st.sidebar.slider("선택한 이미지들의 재생 시간(초)", 0.5, 10.0, 4.0)

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

def process_video(file):
    ext = os.path.splitext(file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
        t.write(file.read())
        clip = VideoFileClip(t.name).without_audio().resized(width=1080)
        if clip.h > 1920: clip = clip.cropped(y_center=clip.h/2, height=1920)
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

# 추가 입력 UI
subtitle_text = st.text_input("자막 입력", "비요일: 당신의 하루를 지켜줄 양우산")
logo = st.file_uploader("2. 브랜드 로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

if st.button("🚀 설정대로 영상 제작 시작"):
    if files and logo:
        with st.spinner('선택하신 이미지의 시간을 개별 적용하여 제작 중입니다...'):
            try:
                # 1. 시간 계산
                video_clips = []
                image_files = []
                total_video_time = 0
                
                for f in files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        v = process_video(f)
                        video_clips.append(v)
                        total_video_time += v.duration
                    else:
                        image_files.append(f)
                
                # 특수 지정 이미지의 총 시간
                total_special_time = len(special_files) * special_img_duration
                # 일반 이미지 개수
                normal_img_count = len(image_files) - len(special_files)
                
                remaining_time = target_total_duration - total_video_time - logo_duration - total_special_time
                
                if remaining_time <= 0 and normal_img_count > 0:
                    st.error("설정한 시간이 부족합니다! 지정한 사진들과 동영상이 너무 길어서 일반 사진을 보여줄 시간이 없어요.")
                    st.stop()
                
                base_img_duration = remaining_time / normal_img_count if normal_img_count > 0 else 0
                
                # 2. 클립 조립
                final_clips = []
                v_idx = 0
                overlap = 0.5
                
                for f in files:
                    if f.name.lower().endswith(('.mp4', '.mov')):
                        c = video_clips[v_idx]
                        v_idx += 1
                    else:
                        # 지정한 파일 목록에 있으면 special_img_duration 적용
                        this_dur = special_img_duration if f.name in special_files else base_img_duration
                        c = process_image(f, this_dur)
                    
                    if len(final_clips) == 0:
                        c = c.with_effects([vfx.CrossFadeOut(overlap)])
                    else:
                        c = c.with_effects([vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)])
                    final_clips.append(c)
                
                l_clip = process_image(logo, logo_duration).with_effects([
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
                
                output = "biyoil_select_final.mp4"
                final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
                st.video(output)
                st.success(f"🎉 완성! 지정 이미지 {len(special_files)}개를 포함해 총 {round(final_video.duration, 1)}초 영상입니다.")
            except Exception as e:
                st.error(f"제작 오류: {e}")
    else:
        st.warning("사진(영상)과 로고를 먼저 올려주세요.")
