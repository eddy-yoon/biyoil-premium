import streamlit as st
import os
import tempfile
import PIL.Image, PIL.ImageFilter, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
import io
import gc

# 1. Pillow 패치 및 환경 설정
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.Resampling = PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

try:
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, afx, CompositeVideoClip
except ImportError:
    st.error("엔진 설치 마무리 중... 1분만 기다린 후 새로고침 해주세요.")
    st.stop()

st.set_page_config(page_title="비요일 얼티밋 v4", page_icon="🎬", layout="wide")

# --- 설정 기억 장치 (Session State) 초기화 ---
if 'subs' not in st.session_state: st.session_state.subs = {}
if 'durs' not in st.session_state: st.session_state.durs = {}

# --- 사이드바: 전역 편집 설정 ---
st.sidebar.header("🎬 전역 편집 설정")
target_total = st.sidebar.number_input("⏱️ 목표 전체 길이(초)", 5, 60, 20)
logo_dur = st.sidebar.slider("🖼️ 로고 노출 시간(초)", 2.0, 5.0, 3.5)
sub_style = st.sidebar.selectbox("🎨 자막 디자인", ["Classic Bar (검정바)", "Modern Shadow (그림자)", "Elegant Border (테두리)"])
# 자막 위치 슬라이더 (0: 바닥, 1920: 천장)
sub_y = st.sidebar.slider("📏 자막 상하 위치 (숫자가 클수록 위로)", 0, 1920, 1600)

# --- 유틸리티 함수 (메모리 최적화형) ---
TARGET_W, TARGET_H = 1080, 1920

def bake_final_frame(pil_img, text="", style="Classic Bar (검정바)", y_pos=1600):
    """이미지+블러배경+자막을 하나의 이미지로 미리 구워버림 (메모리 절약 핵심)"""
    # 1. 블러 배경 생성 (작게 줄여서 연산 후 다시 확대)
    bg = pil_img.resize((TARGET_W//4, TARGET_H//4), PIL.Image.Resampling.NEAREST)
    bg = bg.filter(PIL.ImageFilter.GaussianBlur(radius=5))
    bg = bg.resize((TARGET_W, TARGET_H), PIL.Image.Resampling.LANCZOS)
    
    # 2. 전경 이미지 합성
    fg = PIL.ImageOps.contain(pil_img, (TARGET_W, TARGET_H))
    bg.paste(fg, ((TARGET_W - fg.size[0]) // 2, (TARGET_H - fg.size[1]) // 2))
    
    # 3. 자막 직접 합성 (PIL 사용)
    if text:
        draw = PIL.ImageDraw.Draw(bg)
        try:
            font = PIL.ImageFont.truetype("font.otf", 70)
        except:
            font = PIL.ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx, ty = (TARGET_W - tw) // 2, TARGET_H - th - y_pos
        
        if style == "Classic Bar (검정바)":
            draw.rectangle([tx-30, ty-20, tx+tw+30, ty+th+20], fill=(0, 0, 0, 160))
        elif style == "Modern Shadow (그림자)":
            draw.text((tx+5, ty+5), text, font=font, fill=(0, 0, 0, 150))
        elif style == "Elegant Border (테두리)":
            for ox, oy in [(-3,-3),(3,3),(-3,3),(3,-3)]:
                draw.text((tx+ox, ty+oy), text, font=font, fill=(0, 0, 0, 200))
        
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255))
    
    return bg

# --- 메인 화면 ---
st.title("☔ 비요일 숏폼 스튜디오 [ULTIMATE v4]")
uploaded_files = st.file_uploader("1. 사진/영상 업로드 (세팅 값은 기억됩니다)", accept_multiple_files=True, type=['jpg','png','mp4','mov'])

if uploaded_files:
    tab_edit, tab_preview = st.tabs(["📝 장면별 설정", "🖼️ 실시간 프리뷰"])
    
    with tab_edit:
        cols = st.columns(2)
        for i, f in enumerate(uploaded_files):
            with cols[i % 2]:
                st.write(f"**장면 {i+1}: {f.name}**")
                st.session_state.subs[f.name] = st.text_input(f"자막", key=f"s_{f.name}", value=st.session_state.subs.get(f.name, ""))
                if not f.name.lower().endswith(('.mp4', '.mov')):
                    if st.checkbox("시간 지정", key=f"c_{f.name}"):
                        st.session_state.durs[f.name] = st.slider("초", 0.5, 10.0, st.session_state.durs.get(f.name, 4.0), key=f"d_{f.name}")
                    elif f.name in st.session_state.durs: del st.session_state.durs[f.name]

    with tab_preview:
        p_cols = st.columns(3)
        for i, f in enumerate(uploaded_files):
            with p_cols[i % 3]:
                if f.name.lower().endswith(('.mp4', '.mov')):
                    # 비디오 프리뷰 (첫 프레임만)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                        t.write(f.getvalue())
                        raw = VideoFileClip(t.name)
                        img = PIL.Image.fromarray(raw.get_frame(0))
                        raw.close()
                else:
                    img = PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                
                txt = st.session_state.subs.get(f.name, "")
                preview_baked = bake_final_frame(img, text=txt, style=sub_style, y_pos=sub_y)
                st.image(preview_baked, caption=f"{i+1}번 장면 프리뷰", use_container_width=True)

    st.markdown("---")
    logo = st.file_uploader("2. 로고 업로드", type=['jpg','png'])
    bgm = st.file_uploader("3. 배경음악(MP3) 업로드", type=['mp3'])

    if st.button("🚀 최종 영상 제작 시작 (메모리 최적화 가동)"):
        if not logo: st.error("로고 파일이 필요합니다!")
        else:
            with st.spinner('영상을 굽는 중입니다. 이번엔 절대 꺼지지 않게 조심스럽게 작업할게요...'):
                try:
                    final_clips = []
                    overlap = 0.5
                    
                    # 1. 시간 계산
                    v_clips_info = {}
                    image_files = []
                    total_v_time = 0
                    for f in uploaded_files:
                        if f.name.lower().endswith(('.mp4', '.mov')):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as t:
                                t.write(f.getvalue())
                                vc = VideoFileClip(t.name).without_audio().resized(width=TARGET_W)
                                if vc.h > TARGET_H: vc = vc.cropped(y_center=vc.h/2, height=TARGET_H)
                                # 비디오는 배경과 자막을 Composite로 처리 (비디오니까)
                                bg_f = PIL.Image.fromarray(vc.get_frame(0))
                                bg_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                                # 비디오 배경에는 자막 안 넣음 (자막은 별도 레이어)
                                bake_final_frame(bg_f, text="").save(bg_p)
                                bg_c = ImageClip(bg_p).with_duration(vc.duration)
                                v_clips_info[f.name] = (CompositeVideoClip([bg_c, vc.with_position("center")]), vc.duration)
                                total_v_time += vc.duration
                        else:
                            image_files.append(f)

                    num_total = len(uploaded_files) + 1
                    req_total = target_total + (num_total - 1) * overlap
                    spec_time = sum(st.session_state.durs.values())
                    norm_imgs = [f for f in image_files if f.name not in st.session_state.durs]
                    base_dur = (req_total - total_v_time - logo_dur - spec_time) / len(norm_imgs) if norm_imgs else 0

                    # 2. 클립 제작 (사진은 PIL로 자막까지 구워버림)
                    for f in uploaded_files:
                        txt = st.session_state.subs.get(f.name, "")
                        if f.name in v_clips_info:
                            c, dur = v_clips_info[f.name]
                            if txt: # 비디오 위에 자막 레이어 추가
                                sub_p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                                # 투명 배경에 자막만 그려서 올림
                                sub_img = PIL.Image.new('RGBA', (TARGET_W, TARGET_H), (0,0,0,0))
                                sub_baked = bake_final_frame(PIL.Image.new('RGB',(100,100)), text=txt, style=sub_style, y_pos=sub_y)
                                # bake_final_frame을 자막용으로 재활용하려다 꼬일까봐 직접 자막만 추출하는 로직은 위 create_subtitle_img와 유사하게 처리
                                # (메모리 절약을 위해 여기선 간단한 자막 클립 합성)
                                from moviepy import TextClip # 사용가능시
                                sub_baked.save(sub_p)
                                c = CompositeVideoClip([c, ImageClip(sub_p).with_duration(dur)])
                        else:
                            d = st.session_state.durs.get(f.name, base_dur)
                            raw_img = PIL.Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                            # [핵심] 자막까지 다 포함해서 구워버린 이미지 사용
                            baked_img = bake_final_frame(raw_img, text=txt, style=sub_style, y_pos=sub_y)
                            p = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            baked_img.save(p)
                            c = ImageClip(p).with_duration(d)
                        
                        eff = [vfx.CrossFadeOut(overlap)] if len(final_clips)==0 else [vfx.CrossFadeIn(overlap), vfx.CrossFadeOut(overlap)]
                        final_clips.append(c.with_fps(24).with_effects(eff))

                    # 로고 추가
                    l_img_raw = PIL.Image.open(io.BytesIO(logo.read())).convert("RGB")
                    lp = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    bake_final_frame(l_img_raw, text="").save(lp)
                    final_clips.append(ImageClip(lp).with_duration(logo_dur).with_fps(24).with_effects([vfx.CrossFadeIn(overlap), vfx.Resize(lambda t: 1 + 0.02 * t)]))

                    # 3. 최종 합성
                    res_v = concatenate_videoclips(final_clips, method="compose", padding=-overlap)
                    if bgm:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mt:
                            mt.write(bgm.read())
                            audio = AudioFileClip(mt.name).with_duration(res_v.duration).with_effects([afx.AudioFadeIn(1.0), afx.AudioFadeOut(2.0)])
                            res_v = res_v.with_audio(audio)
                    
                    res_v.write_videofile("final.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="2500k", threads=1)
                    st.video("final.mp4")
                    st.success("🎉 드디어 완성되었습니다!")
                    
                    res_v.close()
                    for c in final_clips: c.close()
                    gc.collect()

                except Exception as e: st.error(f"오류: {e}")
