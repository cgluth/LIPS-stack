import os
import sys
import json
from dotenv import load_dotenv
import requests


class API:
    def __init__(self, config: dict):
        self.config = config

        self.url = config["url"]
        self.method = config.get("method", "POST").upper()
        self.timeout = config.get("timeout", 30)

        # API key from environment
        env_name = config.get("api_key_env", "API_KEY")
        self.api_key = os.getenv(env_name)

        if not self.api_key:
            raise RuntimeError(f"Missing environment variable: {env_name}")

        # Copy headers so config isn't mutated
        self.headers = dict(config.get("headers", {}))
        self.headers["Authorization"] = f"Bearer {self.api_key}"

        # Base payload (model, temperature, etc)
        self.base_payload = dict(config.get("payload", {}))

        # Optional system prompt
        self.system_prompt = config.get("system")

    def get_response(self, prompt: str):
        payload = dict(self.base_payload)

        messages = []

        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        payload["messages"] = messages

        try:
            response = requests.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            raise RuntimeError(f"API request failed: {e}")

        data = response.json()

        # OpenAI-compatible
        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        return data

    def __repr__(self):
        return f"<API {self.method} {self.url}>"


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python api.py config.json \"your prompt\"")
        sys.exit(1)

    config_path = sys.argv[1]
    prompt = sys.argv[2]

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    api = API(config)

    response = api.get_response(prompt)

    print(response)


if __name__ == "__main__":
    load_dotenv()
    main()
