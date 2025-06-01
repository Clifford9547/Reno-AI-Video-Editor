from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
import os
import uuid
import json # 用于读取/写入JSON文件，特别是转录结果

# 导入你的视频处理模块
from .video_processing.processing_tasks import start_processing_stage, get_processing_status_info 
# 引入 LLM 和视频合成的占位符（后续实现）
# from .llm_integration.script_reviser import start_ai_script_generation
# from .video_processing.video_composer import start_final_video_generation

bp = Blueprint('main', __name__)

# --- 辅助函数：获取文件路径 ---
def get_processed_file_path(video_id, filename):
    """根据 video_id 和文件名构造处理后的文件路径"""
    return os.path.join(current_app.config['PROCESSED_MEDIA_FOLDER'], video_id, filename)

@bp.route('/')
def index():
    return render_template('index.html', strings=current_app.config['STRINGS'])

# 路由 1: 视频上传与转录
@bp.route('/upload_and_transcribe', methods=['POST'])
def upload_and_transcribe():
    if 'videoFile' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    file = request.files['videoFile']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    if file:
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        video_id = str(uuid.uuid4())
        unique_filename = video_id + file_extension
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        upload_path = os.path.join(upload_folder, unique_filename)
        
        try:
            file.save(upload_path)
            # 启动第一阶段处理：音频提取和转录
            start_processing_stage(current_app._get_current_object(), video_id, upload_path, 'transcribe')
            
            return jsonify({
                'success': True, 
                'message': '视频上传成功，正在转录...', 
                'video_id': video_id
            }), 202 # 202 Accepted 表示请求已接受，但处理尚未完成
        except Exception as e:
            current_app.logger.error(f"视频上传或保存失败: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'视频上传或保存失败: {e}'}), 500
    
    return jsonify({'success': False, 'message': '未知错误'}), 500

# 路由 2: AI 脚本生成
@bp.route('/generate_ai_script', methods=['POST'])
def generate_ai_script():
    data = request.get_json()
    video_id = data.get('video_id')
    original_script = data.get('original_script')
    theme = data.get('theme')
    target_audience = data.get('target_audience')
    video_purpose = data.get('video_purpose')

    api_url = (data.get('api_url') or '').strip()
    api_method = data.get('api_method', 'POST')
    api_key = (data.get('api_key') or '').strip()
    llm_provider = (data.get('llm_provider') or '').strip().lower()

    # ✅ 自动填充默认 URL（仅当 api_url 未填写时）
    if not api_url and llm_provider:
        if llm_provider == 'openai':
            api_url = 'https://api.openai.com/v1/chat/completions'
        elif llm_provider == 'gemini':
            api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'
        elif llm_provider == 'claude':
            api_url = 'https://api.anthropic.com/v1/messages'

    if not video_id or not api_url:
        return jsonify({'success': False, 'message': '缺少 video_id 或无法确定 API URL'}), 400

    from .video_processing.processing_tasks import video_processing_status
    video_processing_status[video_id]['status'] = 'processing_ai_script'
    video_processing_status[video_id]['progress'] = 0
    video_processing_status[video_id]['message'] = 'AI 脚本生成中...'

    start_processing_stage(
        current_app._get_current_object(),
        video_id,
        None,
        'ai_script_gen',
        original_script=original_script,
        theme=theme,
        target_audience=target_audience,
        video_purpose=video_purpose,
        api_url=api_url,
        api_method=api_method,
        api_key=api_key
    )

    return jsonify({'success': True, 'message': 'AI 脚本生成任务已启动'}), 202



# 路由 3: 最终视频生成
@bp.route('/generate_final_video', methods=['POST'])
def generate_final_video():
    data = request.get_json()
    video_id = data.get('video_id')
    ai_script = data.get('ai_script') # AI 生成的脚本内容

    if not video_id or not ai_script:
        return jsonify({'success': False, 'message': '缺少视频ID或AI脚本'}), 400
    
    # 假设你有一个函数来启动最终视频生成任务
    # start_final_video_generation(current_app._get_current_object(), video_id, ai_script)

    current_app.logger.info(f"最终视频生成请求收到，Video ID: {video_id}")
    # TODO: 实际启动视频合成任务，并更新 get_processing_status_info 中的状态
    from .video_processing.processing_tasks import video_processing_status # 临时导入，需要优化
    video_processing_status[video_id]['status'] = 'processing_video_gen'
    video_processing_status[video_id]['progress'] = 0
    video_processing_status[video_id]['message'] = '最终视频生成中...'

    start_processing_stage(current_app._get_current_object(), video_id, None, 'video_gen', 
                           ai_script=ai_script)

    return jsonify({'success': True, 'message': '最终视频生成任务已启动'}), 202

# 路由 4: 获取处理状态 API
@bp.route('/status_api/<video_id>')
def get_processing_status(video_id):
    status_info = get_processing_status_info(video_id)
    
    # 如果转录完成，尝试读取并返回脚本内容
    if status_info['status'] == 'completed' and status_info.get('stage') == 'transcribe':
        script_path = get_processed_file_path(video_id, "script_with_timestamps.txt")
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                status_info['script_content'] = f.read()
        except FileNotFoundError:
            status_info['script_content'] = '脚本文件未找到。'
    
    # 如果 AI 脚本生成完成，尝试读取并返回 AI 脚本内容
    elif status_info['status'] == 'completed' and status_info.get('stage') == 'ai_script_gen':
        ai_script_path = get_processed_file_path(video_id, "ai_generated_script.txt") # 假设 AI 脚本文件名
        try:
            with open(ai_script_path, 'r', encoding='utf-8') as f:
                status_info['ai_script_content'] = f.read()
        except FileNotFoundError:
            status_info['ai_script_content'] = 'AI 脚本文件未找到。'
            
    return jsonify(status_info)


# 路由 5: 下载原始脚本 (如果需要，目前UI可能不直接使用)
@bp.route('/download_script/<video_id>')
def download_script(video_id):
    script_path = get_processed_file_path(video_id, "script_with_timestamps.txt")
    if os.path.exists(script_path):
        return send_from_directory(os.path.dirname(script_path), os.path.basename(script_path), as_attachment=True)
    else:
        flash('脚本尚未生成或处理失败。')
        return redirect(url_for('main.index')) # 重定向回主页

# 路由 6: 下载最终视频
@bp.route('/download_video/<video_id>')
def download_video(video_id):
    # 假设最终视频名为 final_video.mp4
    video_path = get_processed_file_path(video_id, "final_video.mp4") 
    if os.path.exists(video_path):
        return send_from_directory(os.path.dirname(video_path), os.path.basename(video_path), as_attachment=True)
    else:
        flash('最终视频尚未生成或处理失败。')
        return redirect(url_for('main.index')) # 重定向回主页