"""Local Chatbot with Grounding (Copilot proxy) and Guardrails. Stdlib only."""
import os, re, json
from datetime import datetime
from urllib import request, error

PROXY_URL = os.getenv('COPILOT_PROXY_URL', 'http://localhost:8080/v1')
PROXY_KEY = os.getenv('COPILOT_PROXY_KEY', 'copilot-proxy')
MODEL = os.getenv('COPILOT_PROXY_MODEL', 'gpt-5.4')

MAX_INPUT_LENGTH, MAX_TURNS = 2000, 50
BLOCKED_PATTERNS = [
    r'\b(password|passwd|pwd|secret|api[_-]?key)\s*[:=]\s*\S+',  # Credentials
    r'<script[^>]*>.*?</script>',                                # XSS
    r'\b(DROP|DELETE|INSERT|UPDATE)\s+\w+',                       # SQL injection
]


class Chatbot:
    def __init__(self):
        self.history, self.turns, self.start = [], 0, datetime.now()

    def validate(self, text):
        """Guardrail: reject unsafe/invalid input; returns error string or None."""
        if not text.strip():
            return "Input cannot be empty."
        if len(text) > MAX_INPUT_LENGTH:
            return f"Input too long. Max {MAX_INPUT_LENGTH} characters."
        if any(re.search(p, text, re.IGNORECASE) for p in BLOCKED_PATTERNS):
            return "Input contains potentially unsafe content. Please rephrase."
        if self.turns >= MAX_TURNS:
            return f"Max conversation length ({MAX_TURNS} turns) reached."
        return None

    def filter(self, text):
        """Guardrail: redact any leaked credentials from the response."""
        for p in BLOCKED_PATTERNS:
            text = re.sub(p, '[REDACTED]', text, flags=re.IGNORECASE)
        return text

    def proxy_available(self):
        """Grounding: check the Copilot proxy health endpoint."""
        try:
            url = f"{PROXY_URL.rstrip('/v1')}/health"
            with request.urlopen(url, timeout=5) as r:
                return r.status == 200
        except Exception:
            return False

    def get_response(self, text):
        err = self.validate(text)
        if err:
            return f"⚠️ Guardrail: {err}"
        self.history.append({'role': 'user', 'content': text})
        payload = json.dumps({'model': MODEL, 'messages': self.history,
                              'max_tokens': 500, 'temperature': 0.7}).encode()
        headers = {'Content-Type': 'application/json',
                   'Authorization': f'Bearer {PROXY_KEY}'}
        try:
            req = request.Request(f"{PROXY_URL}/chat/completions", data=payload,
                                  headers=headers, method='POST')
            with request.urlopen(req, timeout=30) as r:
                msg = json.loads(r.read())['choices'][0]['message']['content']
            msg = self.filter(msg)
            self.history.append({'role': 'assistant', 'content': msg})
            self.turns += 1
            return msg
        except error.HTTPError as e:
            return f"❌ HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}"
        except Exception as e:
            return f"❌ Error: {e}"

    def clear(self):
        self.history, self.turns = [], 0
        print("✓ Conversation history cleared.")

    def stats(self):
        print(f"\n{'='*50}\nSession Statistics:")
        print(f"  Duration: {datetime.now() - self.start}")
        print(f"  Turns: {self.turns}/{MAX_TURNS}")
        print(f"  Messages: {len(self.history)}")
        print(f"  Proxy: {PROXY_URL}  Model: {MODEL}\n{'='*50}\n")


def welcome():
    print(f"\n{'='*60}\n🤖 Local Chatbot with Grounding & Guardrails\n{'='*60}")
    print(f"\n📋 Proxy: {PROXY_URL}  |  Model: {MODEL}")
    print("\n🛡️ Guardrails: max input 2000 chars, max 50 turns,"
          " credential/injection blocking, output redaction")
    print("\n💡 Commands: /clear  /stats  /help  /quit")
    print(f"{'='*60}\n")


def main():
    welcome()
    bot = Chatbot()
    if bot.proxy_available():
        print("✓ Copilot proxy is available\n")
    else:
        print("⚠️  Cannot connect to Copilot proxy. Start it in VS Code first.")
        if input("Continue anyway? (y/n): ").strip().lower() != 'y':
            return

    commands = {'/clear': bot.clear, '/stats': bot.stats, '/help': welcome}
    while True:
        try:
            text = input("You: ").strip()
            if not text:
                continue
            if text.lower() in ('/quit', '/exit'):
                print("\n👋 Goodbye!")
                bot.stats()
                break
            if text.startswith('/'):
                action = commands.get(text.lower())
                if action:
                    action()
                else:
                    print("❌ Unknown command. Type /help for options.")
                continue
            print(f"\nBot: {bot.get_response(text)}\n")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            bot.stats()
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}\n")


if __name__ == "__main__":
    main()
