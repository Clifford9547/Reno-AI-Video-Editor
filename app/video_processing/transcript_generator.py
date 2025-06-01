import whisper
import json
import os
from flask import current_app

def transcribe_audio(audio_path):
    """
    使用Whisper模型转录音频，并返回带有时间戳的文本片段。
    模型名称从Flask配置中获取。
    """
    model_name = current_app.config.get('WHISPER_MODEL', 'base')
    print(f"正在加载 Whisper 模型 '{model_name}'...")
    try:
        model = whisper.load_model(model_name) # load_model会在 ~/.cache/whisper 目录下下载模型
        print("Whisper 模型加载完成，开始转录...")
        # verbose=True 可以看到转录过程，word_timestamps=True 获取单词级别的时间戳
        result = model.transcribe(audio_path, verbose=True, word_timestamps=True)
        print("转录完成！")
        return result
    except Exception as e:
        print(f"转录音频时发生错误: {e}")
        return None

def format_transcript_to_script(transcript_result):
    """
    将Whisper的转录结果格式化为带有时间戳的脚本文本。
    """
    script_lines = []
    if not transcript_result or 'segments' not in transcript_result:
        return ""

    for segment in transcript_result['segments']:
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text'].strip()

        # 格式化时间戳 (H:MM:SS.mmm)
        start_h = int(start_time // 3600)
        start_m = int((start_time % 3600) // 60)
        start_s = start_time % 60
        start_formatted = f"{start_h:02}:{start_m:02}:{start_s:06.3f}"

        end_h = int(end_time // 3600)
        end_m = int((end_time % 3600) // 60)
        end_s = end_time % 60
        end_formatted = f"{end_h:02}:{end_m:02}:{end_s:06.3f}"

        script_lines.append(f"[{start_formatted} - {end_formatted}] {text}")
    
    return "\n".join(script_lines)

if __name__ == '__main__':
    # 示例用法
    pass