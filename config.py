import os
import secrets 
import json # 确保 json 模块已导入

# 获取当前文件所在目录的父目录，作为项目根目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- 应用配置 ---
# Flask 安全密钥 (重要：生产环境务必通过环境变量 SECRET_KEY 设置一个强随机字符串！)
SECRET_KEY = os.environ.get('SECRET_KEY') 
if not SECRET_KEY:
    print("警告：SECRET_KEY 环境变量未设置。正在为开发环境生成一个临时密钥。")
    print("在生产环境中，请务必设置一个安全的 SECRET_KEY 环境变量！")
    SECRET_KEY = secrets.token_urlsafe(32) 

# Whisper 模型名称，默认为 'base'，也可通过环境变量 WHISPER_MODEL 覆盖
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base') 

# LLM API 密钥 (未来会用到)，应通过环境变量设置
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')


# --- 国际化 (i18n) 配置 ---
# 修改 LOCALES_DIR 指向新的 app/lib/lang 目录
LOCALES_DIR = os.path.join(BASE_DIR, 'app', 'lib', 'lang') 
# 默认语言代码，与你的文件名（zh-CN.json）匹配
DEFAULT_LANG = os.environ.get('APP_LANGUAGE', 'zh-CN') 


# --- 路径配置 ---
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROCESSED_MEDIA_FOLDER = os.path.join(BASE_DIR, 'processed_media')

FFMPEG_RELATIVE_PATH_IN_PROJECT = 'app/lib/ffmpeg-master-latest-win64-gpl-shared/bin'
FFMPEG_BIN_FULL_DIR = os.path.join(BASE_DIR, FFMPEG_RELATIVE_PATH_IN_PROJECT)


# --- 确保必要的目录存在 ---
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_MEDIA_FOLDER, exist_ok=True)


# --- 运行时配置 FFmpeg PATH ---
if os.path.exists(FFMPEG_BIN_FULL_DIR) and os.path.exists(os.path.join(FFMPEG_BIN_FULL_DIR, 'ffmpeg.exe')):
    if FFMPEG_BIN_FULL_DIR not in os.environ.get('PATH', '').split(os.pathsep):
        os.environ['PATH'] = FFMPEG_BIN_FULL_DIR + os.pathsep + os.environ.get('PATH', '')
        print(f"FFmpeg binary path '{FFMPEG_BIN_FULL_DIR}' 已添加到当前进程的 PATH 中。") 
else:
    print(f"警告：FFmpeg 二进制文件目录 '{FFMPEG_BIN_FULL_DIR}' 不存在或缺少 ffmpeg.exe。") 
    print("这可能导致视频/音频处理功能无法正常工作。请确保 FFmpeg 文件已正确放置。")