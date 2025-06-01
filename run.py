from app import create_app
import os

# 从 .env 文件加载环境变量 (例如，如果未来有API密钥)
from dotenv import load_dotenv
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # 确保 uploads 和 processed_media 目录存在
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('processed_media', exist_ok=True)
    app.run(debug=True) # debug=True 可以在开发时自动重载和显示错误