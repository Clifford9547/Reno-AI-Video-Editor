import os
import json
import threading
from flask import current_app
import time

from app.llm_integration.script_reviser import generate_ai_script
from app.video_processing.video_effects_applier import apply_effects  # 例如你把它封装到这里

from .audio_extractor import extract_audio
from .transcript_generator import transcribe_audio, format_transcript_to_script
# from .ai_script_generator import generate_ai_script_from_llm # 假设未来会有 AI 脚本生成模块
# from .video_composer import compose_final_video # 假设未来会有视频合成模块

# 存储处理状态的字典
# Key: video_id, Value: {
#   'status': 'pending'/'processing'/'completed'/'failed',
#   'progress': int (0-100),
#   'message': str,
#   'stage': 'transcribe'/'ai_script_gen'/'video_gen',
#   'script_path': str (原始脚本路径),
#   'script_content': str (原始脚本内容，方便前端直接读取),
#   'ai_script_path': str (AI脚本路径),
#   'ai_script_content': str (AI脚本内容),
#   'final_video_path': str (最终视频路径),
#   'error': str
# }
video_processing_status = {}

def get_processing_status_info(video_id):
    """
    获取指定视频ID的当前处理状态信息。
    """
    return video_processing_status.get(video_id, {
        'status': 'not_found', 
        'progress': 0, 
        'message': '视频ID不存在或已过期。',
        'stage': 'unknown'
    })

def process_single_stage_task(app, video_id, video_input_path, stage, **kwargs):
    """
    一个通用的后台任务函数，用于处理不同的视频处理阶段。
    video_input_path 仅在 'transcribe' 阶段需要。
    kwargs 用于传递不同阶段所需的额外参数 (如 original_script, theme 等)。
    """
    import json
    import time
    from app.video_processing.audio_extractor import extract_audio
    from app.video_processing.transcript_generator import transcribe_audio, format_transcript_to_script
    from app.video_processing.video_effects_applier import (
        parse_effects_response,
        apply_effects,
        time_to_seconds
    )
    from app.video_processing.effect_manager import apply_text_overlay_with_ffmpeg

    with app.app_context():
        print(f"--- 后台任务开始处理视频 {video_id}，阶段: {stage} ---")
        status_entry = video_processing_status.setdefault(video_id, {
            'status': 'pending', 'progress': 0, 'message': '任务队列中...', 'stage': stage
        })
        status_entry.update({'status': 'processing', 'progress': 0, 'stage': stage})

        output_dir = os.path.join(app.config['PROCESSED_MEDIA_FOLDER'], video_id)
        os.makedirs(output_dir, exist_ok=True)

        try:
            if stage == 'transcribe':
                status_entry['message'] = '正在提取音频...'
                status_entry['progress'] = 10
                audio_output_path = os.path.join(output_dir, "extracted_audio.wav")
                script_output_path = os.path.join(output_dir, "script_with_timestamps.txt")
                json_output_path = os.path.join(output_dir, "whisper_transcript.json")

                if not extract_audio(video_input_path, audio_output_path):
                    raise Exception("音频提取失败")

                status_entry['message'] = '正在转录音频...'
                status_entry['progress'] = 50
                transcript = transcribe_audio(audio_output_path)
                if transcript is None:
                    raise Exception("音频转录失败")

                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript, f, ensure_ascii=False, indent=4)

                formatted_script = format_transcript_to_script(transcript)
                with open(script_output_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_script)

                status_entry['script_path'] = script_output_path
                status_entry['script_content'] = formatted_script
                status_entry['message'] = '视频转录完成。'
                status_entry['progress'] = 100
                status_entry['status'] = 'completed'
                print(f"--- 视频 {video_id} 转录完成 ---")

            elif stage == 'ai_script_gen':
                original_script = kwargs.get('original_script')
                theme = kwargs.get('theme')
                target_audience = kwargs.get('target_audience')
                video_purpose = kwargs.get('video_purpose')
                api_url = kwargs.get('api_url')
                api_method = kwargs.get('api_method', 'POST')
                api_key = kwargs.get('api_key')

                status_entry['message'] = '正在调用 AI 生成脚本...'
                status_entry['progress'] = 20

                from app.llm_integration.script_reviser import generate_ai_script

                try:
                    generated_ai_script, parsed_segments = generate_ai_script(
                        original_script=original_script,
                        theme=theme,
                        target_audience=target_audience,
                        video_purpose=video_purpose,
                        api_url=api_url,
                        api_method=api_method,
                        api_key=api_key
                    )

                    ai_script_output_path = os.path.join(output_dir, "ai_generated_script.txt")
                    with open(ai_script_output_path, 'w', encoding='utf-8') as f:
                        f.write(generated_ai_script)

                    status_entry['ai_script_path'] = ai_script_output_path
                    status_entry['ai_script_content'] = generated_ai_script
                    status_entry['message'] = 'AI 智能脚本生成完成。'
                    status_entry['progress'] = 100
                    status_entry['status'] = 'completed'
                    print(f"--- 视频 {video_id} AI 脚本生成完成 ---")
                except Exception as e:
                    error_message = f"AI 脚本生成失败: {e}"
                    status_entry['status'] = 'failed'
                    status_entry['message'] = error_message
                    status_entry['error'] = error_message
                    print(error_message)

            elif stage == 'video_gen':
                status_entry['message'] = '正在应用特效并合成视频...'
                status_entry['progress'] = 20

                original_video_path = status_entry.get('video_input_path')
                final_video_output_path = os.path.join(output_dir, "final_video.mp4")
                if original_video_path and os.path.exists(original_video_path):
                    print(f"开始真实合成视频: {original_video_path} -> {final_video_output_path}")

                    ai_script_path = os.path.join(output_dir, "ai_generated_script.txt")
                    with open(ai_script_path, 'r', encoding='utf-8') as f:
                        ai_effects_script = f.read()

                    effects_list = parse_effects_response(ai_effects_script)
                    print("[DEBUG] 生成的 effects_list:", effects_list)

                    text_effects_list = []
                    non_text_effects_list = []
                    for effect in effects_list:
                        if effect['code'].startswith('drawtext='):
                            text_effects_list.append({
                                "start": time_to_seconds(effect['start']),
                                "end": time_to_seconds(effect['end']),
                                "drawtext": effect['code']
                            })
                        else:
                            non_text_effects_list.append(effect)

                    if text_effects_list:
                        drawtext_filters = [txt['drawtext'] for txt in text_effects_list]
                        apply_text_overlay_with_ffmpeg(
                            input_path=original_video_path,
                            output_path=final_video_output_path,
                            text_effects_list=drawtext_filters
                        )
                        video_for_next_stage = final_video_output_path
                    else:
                        video_for_next_stage = original_video_path

                    if non_text_effects_list:
                        apply_effects(
                            video_path=video_for_next_stage,
                            output_path=final_video_output_path,
                            effects_list=non_text_effects_list
                        )

                    status_entry['final_video_path'] = final_video_output_path
                    status_entry['message'] = '最终视频生成完成。'
                    status_entry['progress'] = 100
                    status_entry['status'] = 'completed'
                    print(f"--- 视频 {video_id} 最终视频生成完成 ---")
                else:
                    raise Exception("原始视频文件路径丢失或不存在，无法合成视频。")

            else:
                raise ValueError(f"未知处理阶段: {stage}")

        except Exception as e:
            error_message = f"视频处理阶段 '{stage}' 失败: {e}"
            print(error_message)
            status_entry['status'] = 'failed'
            status_entry['error'] = error_message
            status_entry['message'] = error_message
        finally:
            pass

def start_processing_stage(app, video_id, video_input_path, stage, **kwargs):
    """
    启动一个新线程来处理特定阶段的任务。
    在转录阶段，video_input_path 是原始视频路径。
    在后续阶段，kwargs 传递相关参数。
    """
    # 将原始视频路径也存储在状态中，方便后续阶段使用
    if stage == 'transcribe':
        video_processing_status[video_id] = {
            'status': 'pending', 'progress': 0, 'message': '任务队列中...', 'stage': stage,
            'video_input_path': video_input_path # 存储原始视频路径
        }
    else:
        # 对于后续阶段，更新现有状态的 stage
        if video_id not in video_processing_status:
            # 如果是后续阶段，但video_id不存在，可能是错误调用或数据丢失
            print(f"错误：尝试启动未知video_id {video_id} 的 {stage} 阶段任务。")
            return
        video_processing_status[video_id]['stage'] = stage
        video_processing_status[video_id]['status'] = 'pending'
        video_processing_status[video_id]['progress'] = 0
        video_processing_status[video_id]['message'] = f"任务队列中，阶段: {stage}..."

    thread = threading.Thread(target=process_single_stage_task, args=(app, video_id, video_input_path, stage), kwargs=kwargs)
    thread.daemon = True
    thread.start()