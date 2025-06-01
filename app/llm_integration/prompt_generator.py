from flask import current_app
from ..video_processing.effect_manager import get_all_available_effects_for_llm, get_all_available_sound_effects_for_llm

class PromptGenerator:
    def __init__(self):
        self.strings = current_app.config['STRINGS']

    def generate_script_reviser_prompt(self, original_script, theme, target_audience, video_purpose):
        """
        生成用于请求 AI 返回时间点和特效的 Prompt，文字层只生成文字、样式、位置等，不包含 fontfile。
        """
        available_fx = get_all_available_effects_for_llm()
        available_sfx = get_all_available_sound_effects_for_llm()

        fx_list_str = ""
        if available_fx:
            fx_list_str += "以下是可用视觉特效列表：\n"
            for code, desc in available_fx.items():
                fx_list_str += f"- {{FX_{code}}}: {desc}\n"

        sfx_list_str = ""
        if available_sfx:
            sfx_list_str += "以下是可用音效列表：\n"
            for code, desc in available_sfx.items():
                sfx_list_str += f"- {{SFX_{code}}}: {desc}\n"

        prompt_template = """
你是一个专业的视频后期编辑 AI。以下是用户的视频旁白脚本和基本信息。

**原始脚本:**
{original_script}

**用户设置:**
视频主题/风格: {theme}
目标人群: {target_audience}
视频用途: {video_purpose}

**可用视觉特效:**
{fx_list}

**可用音效:**
{sfx_list}

---

你的任务是：
1️⃣ 分析用户脚本和主题，智能推荐哪些时间点适合插入视觉特效或音效。  
2️⃣ 对于文字层特效，请生成以下格式，但**不要包含 fontfile** 参数（示例）：
[00:00:07.120 - 00:00:10.300] drawtext=text='冷到发抖！':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h/4

3️⃣ 其他非文字特效，请保持之前格式（示例）：
[00:00:01.000 - 00:00:03.000] {{FX_FLASH(duration=0.5)}}
[00:00:05.500 - 00:00:06.500] {{SFX_WHOOSH}}

4️⃣ 只输出最终的时间节点+特效格式列表，不要包含解释说明或上下文文字。
"""

        prompt = prompt_template.format(
            original_script=original_script,
            theme=theme,
            target_audience=target_audience,
            video_purpose=video_purpose,
            fx_list=fx_list_str,
            sfx_list=sfx_list_str
        )

        return prompt
