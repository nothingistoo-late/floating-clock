"""
AI Quote Generator (Gemini, OpenAI, Groq, OpenRouter, Offline)
"""
import json
import random
import threading
import urllib.request
from app.core.net_utils import create_secure_ssl_context
from app.messages import AI_PROMPT_TEMPLATE, MOTIVATIONAL_QUOTES

# Alias luôn trỏ tới bản Gemini Flash mới nhất (gemini-1.5-flash đã bị Google ngừng)
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


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
                    quote = self._call_gemini(api_key, context_tag, ai_cfg)
                elif provider in ("openai", "groq", "openrouter", "custom"):
                    quote = self._call_openai_compatible(ai_cfg, context_tag)
                else:
                    quote = self._call_gemini(api_key, context_tag, ai_cfg)
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

    def _call_gemini(self, api_key, context_tag, ai_cfg=None):
        ai_cfg = ai_cfg or {}
        model = str(ai_cfg.get("gemini_model") or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        # API key gửi qua header thay vì query string (tránh lộ key trong URL / log proxy)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FloatingClock/2.1",
            "x-goog-api-key": api_key,
        }
        prompt = AI_PROMPT_TEMPLATE.format(context_tag=context_tag)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.95,
                # Model mới có "thinking" dùng chung ngân sách token → để dư; prompt vẫn yêu cầu câu ngắn
                "maxOutputTokens": 2048
            }
        }
        ctx = create_secure_ssl_context()

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            parts = data["candidates"][0]["content"].get("parts", [])
            # Bỏ qua phần "thought" (nếu có), chỉ lấy văn bản trả lời
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if not text:
                raise ValueError("Gemini không trả về nội dung")
            return text.strip('"\' \n\r')

    def _call_openai_compatible(self, ai_cfg, context_tag):
        api_key = ai_cfg.get("api_key", "").strip()
        provider = ai_cfg.get("provider", "openai")

        cfg_model = str(ai_cfg.get("model") or "").strip()
        cfg_base = str(ai_cfg.get("base_url") or "").strip().rstrip("/")
        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            # Model mặc định của config là "gpt-4o-mini" (OpenAI) — Groq không có → dùng model Groq
            model = cfg_model if cfg_model and cfg_model != "gpt-4o-mini" else "llama-3.3-70b-versatile"
        elif provider == "openrouter":
            # base_url mặc định đang trỏ OpenAI → tự chuyển sang OpenRouter
            if not cfg_base or cfg_base == "https://api.openai.com/v1":
                cfg_base = "https://openrouter.ai/api/v1"
            base_url = cfg_base
            model = cfg_model or "gpt-4o-mini"
            if "/" not in model:
                model = f"openai/{model}"  # OpenRouter cần tiền tố nhà cung cấp
        else:
            base_url = cfg_base or "https://api.openai.com/v1"
            model = cfg_model or "gpt-4o-mini"

        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "FloatingClock/2.1"
        }
        prompt = AI_PROMPT_TEMPLATE.format(context_tag=context_tag)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 60
        }
        ctx = create_secure_ssl_context()

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            return text.strip('"\' \n\r')

    def get_offline_quote(self, context_tag):
        if context_tag in MOTIVATIONAL_QUOTES and MOTIVATIONAL_QUOTES[context_tag]:
            return random.choice(MOTIVATIONAL_QUOTES[context_tag])
        all_q = []
        for v in MOTIVATIONAL_QUOTES.values():
            all_q.extend(v)
        return random.choice(all_q) if all_q else "🚀 Cố lên fen ơi, slay hết mình nào!"

