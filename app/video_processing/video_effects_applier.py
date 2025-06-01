import re
from moviepy.editor import (
    VideoFileClip, CompositeVideoClip
)
from .effect_manager import (
    apply_flash_effect, apply_zoom_in_effect,
    get_sound_effect_clip
)

def parse_effects_response(ai_response_text):
    effect_commands = []
    lines = ai_response_text.strip().split('\n')
    for line in lines:
        time_match = re.match(r"\[(.*?) - (.*?)\]", line)
        if not time_match:
            continue
        start_time = time_match.group(1)
        end_time = time_match.group(2)
        effect_match = re.search(r"\{(.*?)\}", line)
        if not effect_match:
            continue
        effect_code = effect_match.group(1).strip()
        effect_commands.append({
            "start": start_time,
            "end": end_time,
            "code": effect_code
        })
    return effect_commands

def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    return int(h)*3600 + int(m)*60 + float(s)

def apply_effects(video_path, output_path, effects_list):
    clip = VideoFileClip(video_path)
    overlay_clips = []

    for effect in effects_list:
        start = time_to_seconds(effect['start'])
        end = time_to_seconds(effect['end'])
        subclip = clip.subclip(start, end)

        if effect['code'].startswith("FX_FLASH"):
            flash_clip = apply_flash_effect(subclip, duration=0.3, color=(255,255,0), opacity=0.8)
            flash_clip = flash_clip.set_start(start)
            overlay_clips.append(flash_clip)

        elif effect['code'].startswith("FX_ZOOM_IN"):
            zoom_clip = apply_zoom_in_effect(subclip, final_zoom=1.1, duration=(end-start))
            zoom_clip = zoom_clip.set_start(start)
            overlay_clips.append(zoom_clip)

        elif effect['code'].startswith("SFX_CHIME"):
            sfx_clip = get_sound_effect_clip('CHIME', duration=(end-start))
            if sfx_clip:
                clip = clip.set_audio(sfx_clip.set_start(start).audio_fadein(0.1).audio_fadeout(0.1))

        elif effect['code'].startswith("SFX_WHOOSH"):
            sfx_clip = get_sound_effect_clip('WHOOSH', duration=(end-start))
            if sfx_clip:
                clip = clip.set_audio(sfx_clip.set_start(start).audio_fadein(0.1).audio_fadeout(0.1))

    final_clip = CompositeVideoClip([clip] + overlay_clips)
    final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a', remove_temp=True)
