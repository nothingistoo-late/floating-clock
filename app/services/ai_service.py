"""
AI Quote Generator (Gemini, OpenAI, Groq, OpenRouter, Offline)
"""
import json
import random
import ssl
import threading
import urllib.request
from app.constants import DEFAULT_QUOTES


class AIManager:
    """Quản lý sinh câu động viên GenZ qua AI hoặc offline fallback"""
    def __init__(self, config):
        self.config = config
        self.is_fetching = False

    def fetch_ai_quote(self, context_tag, callback=None, dispatcher=None):
        """
        Gọi API AI trong background thread để tạo câu động viên GenZ theo ngữ cảnh.
        dispatcher: hàm dispatch (root.after(0, ...)) để đưa kết quả về luồng chính an toàn.
        """
        ai_cfg = self.config.get("ai_quotes", {})
        api_key = ai_cfg.get("api_key", "").strip()
        provider = ai_cfg.get("provider", "gemini")

        if not api_key:
            quote = self.get_offline_quote(context_tag)
            if callback:
                if dispatcher:
                    dispatcher(lambda: callback(quote, is_ai=False, error=None))
                else:
                    callback(quote, is_ai=False, error=None)
            return

        if self.is_fetching:
            return
        self.is_fetching = True

        def _worker():
            quote = None
            err = None
            try:
                if provider == "gemini":
                    quote = self._call_gemini(api_key, context_tag)
                elif provider in ("openai", "groq", "openrouter", "custom"):
                    quote = self._call_openai_compatible(ai_cfg, context_tag)
                else:
                    quote = self._call_gemini(api_key, context_tag)
            except Exception as e:
                err = str(e)
                quote = self.get_offline_quote(context_tag)
            finally:
                self.is_fetching = False
                if callback:
                    is_ai_success = (err is None and quote is not None)
                    if dispatcher:
                        dispatcher(lambda: callback(quote, is_ai=is_ai_success, error=err))
                    else:
                        callback(quote, is_ai=is_ai_success, error=err)

        threading.Thread(target=_worker, daemon=True).start()

    def _call_gemini(self, api_key, context_tag):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json", "User-Agent": "FloatingClock/2.1"}
        prompt = (
            "Hãy tạo DUY NHẤT 1 câu động viên làm việc ngắn gọn (dưới 15 từ), cực kỳ hài hước, mang đậm phong cách GenZ Việt Nam "
            "(sử dụng linh hoạt từ ngữ trend như: slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking, hết nước chấm, bro, fen, gét gô...) "
            f"phù hợp với ngữ cảnh: {context_tag}. Chỉ trả về duy nhất nội dung câu nói kèm icon biểu cảm (emoji), không thêm giải thích hay dấu ngoặc kép."
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.95,
                "maxOutputTokens": 60
            }
        }
        try:
            ctx = ssl._create_unverified_context()
        except Exception:
            ctx = None

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text.strip('"\' \n\r')

    def _call_openai_compatible(self, ai_cfg, context_tag):
        api_key = ai_cfg.get("api_key", "").strip()
        provider = ai_cfg.get("provider", "openai")

        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            model = ai_cfg.get("model") or "llama-3.3-70b-versatile"
        else:
            base_url = ai_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
            model = ai_cfg.get("model", "gpt-4o-mini").strip() or "gpt-4o-mini"

        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "FloatingClock/2.1"
        }
        prompt = (
            "Hãy tạo DUY NHẤT 1 câu động viên làm việc ngắn gọn (dưới 15 từ), cực kỳ hài hước, mang đậm phong cách GenZ Việt Nam "
            "(sử dụng linh hoạt từ ngữ trend như: slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking, hết nước chấm, bro, fen, gét gô...) "
            f"phù hợp với ngữ cảnh: {context_tag}. Chỉ trả về duy nhất nội dung câu nói kèm icon biểu cảm (emoji), không thêm giải thích hay dấu ngoặc kép."
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 60
        }
        try:
            ctx = ssl._create_unverified_context()
        except Exception:
            ctx = None

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            return text.strip('"\' \n\r')

    def get_offline_quote(self, context_tag):
        if context_tag in DEFAULT_QUOTES and DEFAULT_QUOTES[context_tag]:
            return random.choice(DEFAULT_QUOTES[context_tag])
        all_q = []
        for v in DEFAULT_QUOTES.values():
            all_q.extend(v)
        return random.choice(all_q) if all_q else "🚀 Cố lên fen ơi, slay hết mình nào!"
