from flask import Flask, g, session, request, redirect, url_for 
import os
import json

def create_app():
    app = Flask(__name__)
    # 从项目根目录的 config.py 加载配置
    app.config.from_pyfile(os.path.join(app.root_path, '..', 'config.py')) 
    
    # --- 加载语言字符串 ---
    app.translations = {} # 初始化翻译字典，用于存储所有语言的翻译
    
    # 从 config.py 获取语言文件目录和默认语言
    locales_dir = app.config.get('LOCALES_DIR')
    default_lang = app.config.get('DEFAULT_LANG')

    # DEBUG: 打印从 config.py 获取的路径和默认语言
    print(f"DEBUG: locales_dir from config: {locales_dir}") 
    print(f"DEBUG: default_lang from config: {default_lang}") 
    
    # 确保 locales_dir 存在，否则无法加载翻译
    if not locales_dir or not os.path.exists(locales_dir):
        app.logger.error(f"错误：语言文件目录 '{locales_dir}' 不存在或未在 config.py 中正确配置。")
        app.translations = {} # 设置为空，避免后续错误
    else:
        # 遍历语言文件目录，加载所有 JSON 语言文件
        for filename in os.listdir(locales_dir):
            if filename.endswith('.json'):
                lang_code = os.path.splitext(filename)[0] # 获取语言代码，例如 'zh-CN'
                filepath = os.path.join(locales_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        app.translations[lang_code] = json.load(f)
                    print(f"已加载语言文件: {filepath}")
                except Exception as e:
                    app.logger.error(f"无法加载语言文件 {filepath}: {e}")
                    print(f"DEBUG: 加载语言文件 {filepath} 失败，错误: {e}") 
            
    # *** 关键修正：将加载到的默认语言翻译赋值给 app.config['STRINGS'] ***
    app.config['STRINGS'] = app.translations.get(default_lang, {})
    


        # --- 创建音效目录（必须在 app_context 中执行） ---
    from .video_processing.effect_manager import get_sfx_preset_path, get_sfx_user_uploaded_path
    with app.app_context():
        os.makedirs(get_sfx_preset_path(), exist_ok=True)
        os.makedirs(get_sfx_user_uploaded_path(), exist_ok=True)
        app.logger.info(f"音效目录已创建: {get_sfx_preset_path()} 和 {get_sfx_user_uploaded_path()}")

    
    if not app.config['STRINGS']:
        app.logger.warning(f"警告：未找到默认语言 '{default_lang}' 的翻译，或翻译文件为空。")
        
    # 定义翻译函数 (供视图函数和后台任务使用)
    def get_text(key, **kwargs):
        # 从 g 对象获取当前请求的语言，如果没有则使用 app.config 中的默认语言
        lang = getattr(g, 'lang', app.config['DEFAULT_LANG']) 

        # 如果请求的语言不存在翻译，回退到默认语言的翻译
        translations_for_current_lang = app.translations.get(lang, app.translations.get(app.config['DEFAULT_LANG'], {}))
        
        # 如果翻译键不存在，返回一个提示信息
        text = translations_for_current_lang.get(key, f"MISSING_TRANSLATION_KEY[{key}]")
        
        # 格式化文本中的占位符 (例如：{name} 会被替换)
        return text.format(**kwargs)

    # 将翻译函数添加到 Jinja2 全局上下文，使其在所有模板中可用 (例如 {{ _('key') }})
    @app.context_processor
    def inject_translation_function():
        # 这里也确保将 'strings' 传递给模板，与 routes.py 中的 render_template 保持一致
        # 这样在模板中可以直接使用 {{ strings.key }}
        return dict(_=get_text, strings=app.config['STRINGS']) # 确保 strings 变量被传递

    # 在每个请求前设置当前语言，并确保 g._ 函数可用
    @app.before_request
    def set_g_lang():
        # 尝试从 session 获取语言偏好，否则使用配置中的默认语言
        session_lang = session.get('lang', app.config['DEFAULT_LANG'])
        # 验证 session_lang 是否是我们已加载的有效语言
        if session_lang not in app.translations:
            session_lang = app.config['DEFAULT_LANG'] # 如果无效，回退到默认语言
            session['lang'] = session_lang # 确保 session 存储的也是有效语言
        
        g.lang = session_lang # 将当前请求的语言存储到 g 对象
        g._ = get_text       # 将翻译函数绑定到 g 对象，方便在视图函数中使用

    # 处理语言切换路由
    @app.route('/set_lang/<lang_code>')
    def set_language(lang_code):
        if lang_code in app.translations:
            session['lang'] = lang_code
        else:
            session['lang'] = app.config['DEFAULT_LANG'] # 如果语言代码无效，则设置为默认语言
        # 重定向回用户上一个页面，或者到主页
        return redirect(request.referrer or url_for('main.index'))


    # 注册蓝图
    from . import routes
    app.register_blueprint(routes.bp)
    print("\n[Flask 已注册的可用路由]:")
    print(app.url_map)


    return app

