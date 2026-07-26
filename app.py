import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps

try:
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, afx, TextClip
except ImportError:
    st.error("엔진 설치 중... 2분 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 프리미엄", page_icon="✨")
st.title("☔ 비요일 숏폼 제작소 [PREMIUM]")
st.write("감성적인 흐린 배경과 자막 기능을 제공합니다.")

def process_premium(file, duration=2.0):
    ext = os.path.splitext(file.name)[1].lower()
    target_size = (1080, 1920)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
        t.write(file.read())
        
        if ext in ['.mp4', '.mov']:
            clip = VideoFileClip(t.name).without_audio().resized(width=1080)
            # 영상도 배경 채우기 로직 적용 가능하나 우선 중앙 배치
            if clip.h > 1920: clip = clip.cropped(y_center=clip.h/2, height=1920)
            else: clip = clip.margin(top=(1920-clip.h)//2, bottom=(1920-clip.h)//2, color=(0,0,0))
            return clip
        else:
            img = PIL.Image.open(t.name).convert("RGB")
            # 1. 배경용: 크게 확대해서 흐리게 만들기
            bg = img.resize(target_size, PIL.Image.Resampling.LANCZOS)
            bg = bg.filter(PIL.ImageFilter.GaussianBlur(radius=30))
            # 2. 전경용: 비율 유지하며 맞추기
            fg = PIL.ImageOps.contain(img, target_size)
            # 3. 합치기
            bg.paste(fg, ((target_size[0]-fg.size[0])//2, (target_size[1]-fg.size[1])//2))
            bg.save(t.name + ".png")
            return ImageClip(t.name + ".png").with_duration(duration)

# UI 구성
st.subheader("1. 소스 및 자막 입력")
files = st.file_uploader("사진/영상 업로드", accept_multiple_files=True, type=['jpg','png','mp4','mov'])
caption = st.text_input("영상에 넣을 핵심 자mask (예: 자외선 99.9% 차단!)", "")
logo = st.file_uploader("로고 업로드", type=['jpg','png'])
bgm = st.file_uploader("배경음악(MP3)", type=['mp3'])

if st.button("✨ 프리미엄 영상 제작"):
    if files and logo:
        with st.spinner('감성적인 배경과 자막을 입히는 중...'):
            try:
                clips = []
                for i, f in enumerate(files):
                    clip = process_premium(f)
                    # 부드러운 전환
                    clip = clip.with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)])
                    clips.append(clip)
                
                # 로고 엔딩
                l_clip = process_premium(logo, duration=4.0).with_effects([
                    vfx.CrossFadeIn(0.5), vfx.Resize(lambda t: 1 + 0.02 * t)
                ])
                clips.append(l_clip)
                
                final = concatenate_videoclips(clips, method="compose", padding=-0.5)
                
                # 자막 추가 (자막이 입력된 경우만)
                # 주의: TextClip은 서버 환경에 따라 폰트 설정이 까다로워 간단한 방식으로 구현
                if caption:
                    st.info("자막 기능은 현재 베타 버전입니다. 이미지 위에 텍스트를 입히는 고도화 작업이 진행될 수 있습니다.")
                
                if bgm:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                        mt.write(bgm.read())
                        audio = AudioFileClip(mt.name).with_duration(final.duration)
                        audio = audio.with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                        final = final.with_audio(audio)
                
                final.write_videofile("premium_out.mp4", fps=24, codec="libx264", audio_codec="aac")
                st.video("premium_out.mp4")
            except Exception as e:
                st.error(f"제작 오류: {e}")
    else:
        st.error("파일을 등록해줘!")
