import requests
from flask import current_app

class LLMManager:
    def __init__(self, api_url, api_method='POST', api_key=None):
        self.api_url = api_url
        self.api_method = api_method.upper()
        self.api_key = api_key

    def generate_text(self, prompt, max_tokens=2000, temperature=0.7):
        import requests

        # ✅ Gemini 特殊处理: 如果是 Gemini 且 URL 中没 key=，就自动拼到 URL
        if 'generativelanguage.googleapis.com' in self.api_url and 'key=' not in self.api_url and self.api_key:
            connector = '&' if '?' in self.api_url else '?'
            self.api_url = f"{self.api_url}{connector}key={self.api_key}"

        headers = {
            'Content-Type': 'application/json'
        }

        # ✅ 非 Gemini，才需要 Authorization header
        if self.api_key and 'generativelanguage.googleapis.com' not in self.api_url and 'key=' not in self.api_url:
            headers['Authorization'] = f'Bearer {self.api_key}'

        # ⭐ 根据不同 API 区分请求体格式
        if 'generativelanguage.googleapis.com' in self.api_url:
            # Gemini API
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
        else:
            # OpenAI / Claude / 自定义 API
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

        try:
            response = requests.request(
                self.api_method,
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            # 处理返回结果
            try:
                data = response.json()
                # ✅ Gemini 格式处理
                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                # 通用
                return data.get("script") or data.get("content") or response.text
            except Exception:
                return response.text

        except Exception as e:
            current_app.logger.error(f"LLM API 请求失败: {e}", exc_info=True)
            raise RuntimeError(f"LLM 请求失败: {e}")
