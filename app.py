import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont

try:
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, afx, CompositeVideoClip
except ImportError:
    st.error("엔진 설치 중... 2분 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 프리미엄", page_icon="✨")
st.title("☔ 비요일 숏폼 제작소 [PREMIUM]")
st.write("Pretendard 자막과 감성 배경 효과를 지원합니다.")

# 9:16 규격
TARGET_W, TARGET_H = 1080, 1920

def create_subtitle_image(text, font_path, font_size=60):
    """PIL을 사용하여 자막 이미지를 생성합니다."""
    # 투명한 레이어 생성
    img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    
    try:
        font = PIL.ImageFont.truetype(font_path, font_size)
    except:
        # 폰트 로드 실패 시 기본 폰트 사용
        font = PIL.ImageFont.load_default()
        st.warning("폰트 파일을 찾을 수 없어 기본 폰트로 대체합니다. font.otf 파일을 확인해주세요.")

    # 텍스트 위치 계산 (하단 중앙)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - 200 # 하단에서 200픽셀 위
    
    # 가독성을 위한 반투명 검정 배경 박스
    padding = 20
    draw.rectangle([tx - padding, ty - padding, tx + tw + padding, ty + th + padding], fill=(0, 0, 0, 150))
    
    # 텍스트 쓰기
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    
    temp_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
    img.save(temp_p)
    return temp_p

def process_premium(file, duration=2.0):
    ext = os.path.splitext(file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
        t.write(file.read())
        if ext in ['.mp4', '.mov']:
            clip = VideoFileClip(t.name).without_audio().resized(width=1080)
            if clip.h > 1920: clip = clip.cropped(y_center=clip.h/2, height=1920)
            else: clip = clip.margin(top=(1920-clip.h)//2, bottom=(1920-clip.h)//2, color=(0,0,0))
        else:
            img = PIL.Image.open(t.name).convert("RGB")
            bg = img.resize((1080, 1920), PIL.Image.Resampling.LANCZOS).filter(PIL.ImageFilter.GaussianBlur(radius=30))
            fg = PIL.ImageOps.contain(img, (1080, 1920))
            bg.paste(fg, ((1080-fg.size[0])//2, (1920-fg.size[1])//2))
            bg.save(t.name + ".png")
            clip = ImageClip(t.name + ".png").with_duration(duration)
    return clip.with_fps(24)

# UI
files = st.file_uploader("사진/영상 업로드", accept_multiple_files=True, type=['jpg','png','mp4','mov'])
subtitle_text = st.text_input("영상에 넣을 자막 입력", "비요일: 당신의 하루를 지켜줄 양우산")
logo = st.file_uploader("로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("배경음악(MP3)", type=['mp3'])

if st.button("✨ 프리미엄 영상 제작"):
    if files and logo:
        with st.spinner('Pretendard 자막을 입히는 중...'):
            try:
                clips = [process_premium(f).with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)]) for f in files]
                l_clip = process_premium(logo, duration=4.0).with_effects([vfx.CrossFadeIn(0.5), vfx.Resize(lambda t: 1 + 0.02 * t)])
                clips.append(l_clip)
                
                # 영상 합치기
                video_only = concatenate_videoclips(clips, method="compose", padding=-0.5)
                
                # 자막 오버레이 추가
                if subtitle_text:
                    font_file = "font.otf" # GitHub에 올린 폰트 파일명
                    sub_img_path = create_subtitle_image(subtitle_text, font_file)
                    sub_clip = ImageClip(sub_img_path).with_duration(video_only.duration).with_fps(24)
                    # 영상과 자막 합성
                    final_video = CompositeVideoClip([video_only, sub_clip])
                else:
                    final_video = video_only
                
                # 오디오 처리
                if bgm:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                        mt.write(bgm.read())
                        audio = AudioFileClip(mt.name).with_duration(final_video.duration)
                        audio = audio.with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                        final_video = final_video.with_audio(audio)
                
                output = "biyoil_premium_subtitle.mp4"
                final_video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
                st.video(output)
                st.success("🎉 자막까지 완벽한 프리미엄 영상 완성!")
            except Exception as e:
                st.error(f"에러 발생: {e}")
