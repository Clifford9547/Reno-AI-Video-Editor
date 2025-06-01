import os
import subprocess
from flask import current_app
from moviepy.editor import VideoFileClip, CompositeVideoClip


# 🎥 视觉特效：闪烁
def apply_flash_effect(clip, duration=0.3, color=(255,255,255), opacity=0.8):
    from moviepy.video.fx.all import fadein, fadeout
    flash = clip.fx(fadein, duration).fx(fadeout, duration).fl_image(
        lambda frame: (frame * opacity).astype('uint8'))
    return CompositeVideoClip([clip, flash])

# 🎥 视觉特效：缩放
def apply_zoom_in_effect(clip, final_zoom=1.1, duration=1):
    return clip.resize(lambda t: 1 + (final_zoom - 1) * (t / duration))

# 🔊 音效获取
SFX_PRESET_DIR_NAME = 'sfx'  # 音效目录
def get_sfx_preset_path():
    return os.path.join(current_app.root_path, 'lib', SFX_PRESET_DIR_NAME)

def get_sound_effect_path(sfx_name):
    preset_path_mp3 = os.path.join(get_sfx_preset_path(), f"{sfx_name.lower()}.mp3")
    if os.path.exists(preset_path_mp3):
        return preset_path_mp3
    current_app.logger.warning(f"音效文件 '{sfx_name}' 未找到。")
    return None

def get_sound_effect_clip(sfx_name, duration=1):
    sfx_path = get_sound_effect_path(sfx_name)
    if sfx_path:
        from moviepy.editor import AudioFileClip
        return AudioFileClip(sfx_path).subclip(0, duration)
    return None

def apply_text_overlay_with_ffmpeg(input_path, output_path, text_effects_list):
    """
    text_effects_list: [
        {
            "start": 7.12,
            "end": 10.3,
            "drawtext": "drawtext=text='你好':fontsize=36:fontcolor=white:fontfile=/path/to/font.ttf:x=(w-text_w)/2:y=h/4"
        },
        ...
    ]
    """
    import subprocess
    import os
    from flask import current_app

    # 1️⃣ 生成项目内字体文件路径（你在 lib/fonts 里放置了 SimSun.ttf）
    font_path = os.path.join(current_app.root_path, 'app', 'lib', 'fonts', 'simhei.ttf').replace('\\', '/')

    filter_complex_parts = []

    for effect in text_effects_list:
        # 2️⃣ 自动把 AI 生成的 /path/to/font.ttf 替换成项目内真实可用字体
        drawtext_filter = effect['drawtext'] + f":fontfile='{font_path}'"

        filter_complex_parts.append(drawtext_filter)

    # 3️⃣ 拼接完整的 filter_complex
    filter_complex = ",".join(filter_complex_parts)

    # 4️⃣ ffmpeg 命令行拼接
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', filter_complex,
        '-c:a', 'copy', output_path
    ]
    print("[DEBUG] ffmpeg 命令:", " ".join(cmd))

    # 5️⃣ 执行 ffmpeg 命令
    subprocess.run(cmd, check=True)

# 🔍 供 LLM / 前端查询可用特效列表
EFFECT_LIBRARY = {
    'FLASH': {
        'function': apply_flash_effect,
        'description': '在指定时间段插入闪烁特效',
        'params_info': {
            'duration': '闪烁持续时间（秒）',
            'color': '闪烁颜色 (R,G,B)',
            'opacity': '透明度 (0-1)'
        }
    },
    'ZOOM_IN': {
        'function': apply_zoom_in_effect,
        'description': '在指定时间段插入缩放特效',
        'params_info': {
            'final_zoom': '缩放倍数',
            'duration': '缩放持续时间（秒）'
        }
    },
    # 🟡 文字叠加现在改用 ffmpeg，已不再这里声明
}

def get_sfx_user_uploaded_path():
    return os.path.join(current_app.root_path, 'lib', 'sfx_user_uploaded')

def get_all_available_effects_for_llm():
    return {code: f"{info['description']} (参数: {', '.join(info['params_info'].keys())})"
            for code, info in EFFECT_LIBRARY.items()}

def get_all_available_sound_effects_for_llm():
    sfx_dir = get_sfx_preset_path()
    if not os.path.exists(sfx_dir):
        return {}
    return {file.split('.')[0].upper(): f"可用音效: {file}"
            for file in os.listdir(sfx_dir) if file.endswith('.mp3')}
