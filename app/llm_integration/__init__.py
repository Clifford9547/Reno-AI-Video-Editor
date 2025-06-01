from flask import Flask
import os # 导入 os 模块，用于处理文件路径

def create_app():
    # 创建 Flask 应用实例
    app = Flask(__name__)
    
    # 构建 config.py 文件的绝对路径
    # app.root_path 会指向 app 文件夹的绝对路径 (例如 D:\Projects\reno_ai_video_editor\app)
    # os.path.join(app.root_path, '..', 'config.py') 会向上回退一级目录，指向项目根目录下的 config.py
    config_path = os.path.join(app.root_path, '..', 'config.py')
    
    # 检查 config.py 文件是否存在，如果不存在则打印错误并抛出异常
    # 这是一个好的实践，可以在启动时就发现配置问题
    if not os.path.exists(config_path):
        error_message = f"错误：配置文件 config.py 未找到。期望路径：{config_path}"
        print(error_message)
        raise FileNotFoundError(error_message)

    # 从构建的路径加载配置文件
    app.config.from_pyfile(config_path) 

    # 注册蓝图 (routes.py 中定义的路由)
    # . 表示当前包 (app 目录)，所以 from . import routes 会导入 app/routes.py
    from . import routes
    app.register_blueprint(routes.bp)

    return app