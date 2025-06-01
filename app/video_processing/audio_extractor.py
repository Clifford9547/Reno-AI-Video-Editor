import moviepy.editor as mp
import os

def extract_audio(video_path, audio_output_path):
    """
    从视频中提取音频并保存为WAV格式。
    返回提取成功与否的布尔值。
    """
    try:
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        # 确保输出目录存在
        os.makedirs(os.path.dirname(audio_output_path), exist_ok=True)
        audio.write_audiofile(audio_output_path, codec='pcm_s16le') # 保存为高质量WAV
        print(f"音频已成功提取到: {audio_output_path}")
        return True
    except Exception as e:
        print(f"提取音频时发生错误: {e}")
        return False

if __name__ == '__main__':
    # 示例用法，但在Flask应用中会通过其他方式调用
    pass