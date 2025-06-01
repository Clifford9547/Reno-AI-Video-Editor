from flask import current_app
from .llm_manager import LLMManager # 从本地导入 LLMManager
from .prompt_generator import PromptGenerator # 从本地导入 PromptGenerator
import re # 用于解析 LLM 返回的脚本中的占位符

# 用于解析特效占位符的正则表达式
# 匹配 {FX_CODE} 或 {FX_CODE(param=value,...)}
FX_PLACEHOLDER_PATTERN = re.compile(r'\{FX_([A-Z_]+)(?:\((.*?)\))?\}')
# 匹配 {SFX_CODE}
SFX_PLACEHOLDER_PATTERN = re.compile(r'\{SFX_([A-Z_]+)\}')

def parse_llm_generated_script(script_text):
    """
    解析 LLM 生成的脚本，提取文本和特效指令。
    返回一个列表，每个元素是 (text_segment, effect_list) 或 (text_segment, sfx_list)
    """
    parsed_segments = []
    last_idx = 0

    # 找到所有占位符及其位置
    all_placeholders = []
    for match in FX_PLACEHOLDER_PATTERN.finditer(script_text):
        all_placeholders.append((match.start(), match.end(), 'fx', match.group(1), match.group(2)))
    for match in SFX_PLACEHOLDER_PATTERN.finditer(script_text):
        all_placeholders.append((match.start(), match.end(), 'sfx', match.group(1), None))
    
    # 按出现顺序排序
    all_placeholders.sort(key=lambda x: x[0])

    for start_idx, end_idx, p_type, code, params_str in all_placeholders:
        # 添加占位符之前的文本
        if start_idx > last_idx:
            text_segment = script_text[last_idx:start_idx].strip()
            if text_segment:
                parsed_segments.append({'type': 'text', 'content': text_segment})
        
        # 添加占位符指令
        params = {}
        if params_str:
            # 尝试解析参数字符串 (简单的键值对解析)
            try:
                # 使用 ast.literal_eval 更安全，但需要导入 ast
                # eval 存在安全风险，仅在内部确定来源时使用，或用更安全的解析器
                # 这里简单处理，要求 LLM 输出标准 Python 字典格式的参数
                # 或者手动解析 key=value, key2=value2 格式
                param_pairs = params_str.split(',')
                for pair in param_pairs:
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        # 尝试转换为 Python 类型
                        try:
                            params[k] = eval(v) # 注意：eval 存在安全风险，生产环境需替换为更安全的解析
                        except (SyntaxError, NameError):
                            params[k] = v # 如果无法eval，当作字符串处理
            except Exception as e:
                current_app.logger.warning(f"解析占位符参数失败: {params_str}，错误: {e}")
                params = {} # 解析失败则参数为空

        if p_type == 'fx':
            parsed_segments.append({'type': 'fx', 'code': code, 'params': params})
        elif p_type == 'sfx':
            parsed_segments.append({'type': 'sfx', 'code': code, 'params': params}) # 音效目前无参数，但保留结构

        last_idx = end_idx
    
    # 添加最后一个占位符之后的文本
    if last_idx < len(script_text):
        text_segment = script_text[last_idx:].strip()
        if text_segment:
            parsed_segments.append({'type': 'text', 'content': text_segment})
            
    return parsed_segments

def generate_ai_script(original_script, theme, target_audience, video_purpose, api_url, api_method, api_key):
    strings = current_app.config['STRINGS']
    prompt_generator = PromptGenerator()
    llm_manager = LLMManager(api_url, api_method, api_key)  # 关键修改

    prompt = prompt_generator.generate_script_reviser_prompt(
        original_script, theme, target_audience, video_purpose
    )
    print("🔍 Prompt 内容如下：\n", prompt)

    try:
        generated_script_text = llm_manager.generate_text(prompt)
        current_app.logger.info("LLM 成功生成脚本。")
        parsed_script = parse_llm_generated_script(generated_script_text)
        print("📩 AI 返回的脚本如下：\n", generated_script_text)
        return generated_script_text, parsed_script
    except Exception as e:
        current_app.logger.error(f"AI 脚本生成失败: {e}", exc_info=True)
        error_script = strings.get('llm_generation_failed_placeholder', 'AI 脚本生成失败。') + f"\n错误信息: {e}"
        return error_script, [{'type': 'text', 'content': error_script}]
