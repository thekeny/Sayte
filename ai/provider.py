import requests

import config


class Provider:
    def __init__(self, profile):
        self.url = profile["url"].strip().rstrip("/")
        self.key = profile["api_key"].strip()
        self.kind = profile["kind"]

    def request(self, method, endpoint, payload=None):
        if self.kind == "openrouter" and not self.key:
            raise ValueError(config.AI_ERRORS["missing_key"])
        headers = {}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        try:
            response = requests.request(
                method, self.url + endpoint, headers=headers,
                json=payload, timeout=config.AI_TIMEOUT,
                allow_redirects=False
            )
        except requests.Timeout:
            raise ValueError(config.AI_ERRORS["timeout"]) from None
        except requests.RequestException:
            raise ValueError(config.AI_ERRORS["connection"]) from None
        with response:
            if not 200 <= response.status_code < 300:
                raise ValueError(config.AI_HTTP_ERRORS.get(
                    response.status_code,
                    config.AI_ERRORS["http"].format(status=response.status_code)
                ))
            try:
                data = response.json()
            except ValueError:
                raise ValueError(config.AI_ERRORS["json"]) from None
        if not isinstance(data, dict):
            raise ValueError(config.AI_ERRORS["format"])
        if "error" in data:
            raise ValueError(config.AI_ERRORS["provider"])
        return data

    def getModels(self):
        data = self.request("GET", "/models")
        rows = data.get("data")
        if not isinstance(rows, list):
            raise ValueError(config.AI_ERRORS["models"])
        models = {}
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                modelId = row["id"].strip()
                if modelId:
                    name = row.get("name")
                    models[modelId] = (name if isinstance(name, str)
                                       else modelId)
        return [{"id": key, "name": value}
                for key, value in sorted(models.items())]

    def processText(self, model, prompt, text):
        if not model.strip() or not prompt.strip() or not text.strip():
            raise ValueError(config.AI_ERRORS["input"])
        data = self.request("POST", "/chat/completions", {
            "model": model.strip(),
            "messages": [
                {"role": "system", "content": config.AI_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Действие:\n{prompt.strip()}\n\nТекст заметки:\n{text}"
                )}
            ],
            "stream": False
        })
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ValueError(config.AI_ERRORS["result"]) from None
        if not isinstance(text, str) or not text.strip():
            raise ValueError(config.AI_ERRORS["empty"])
        return text.strip()
