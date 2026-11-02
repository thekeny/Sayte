import os
from pathlib import Path

import config


class Whisper:
    def __init__(self):
        self.model = None

    def transcribe(self, audio):
        if audio.size == 0:
            return ""

        if self.model is None:
            # Публичная модель скачивается без аккаунта и Xet-авторизации.
            os.environ["HF_HUB_DISABLE_XET"] = "1"
            os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
            from faster_whisper import WhisperModel
            from faster_whisper.utils import download_model
            from huggingface_hub.errors import LocalEntryNotFoundError

            cache = config.BASE_DIR / "data" / "models"
            try:
                path = download_model(
                    config.WHISPER_MODEL, cache_dir=str(cache),
                    local_files_only=True, use_auth_token=False
                )
            except LocalEntryNotFoundError:
                path = None

            files = ("model.bin", "config.json", "tokenizer.json")
            if path is None or not all(
                (Path(path) / name).is_file() for name in files
            ):
                try:
                    path = download_model(
                        config.WHISPER_MODEL, cache_dir=str(cache),
                        use_auth_token=False
                    )
                except Exception as error:
                    raise RuntimeError(
                        "Не удалось скачать публичную модель Whisper. "
                        "Токен и аккаунт не нужны. Проверьте подключение "
                        "и доступ к huggingface.co, затем повторите запись.\n"
                        f"Подробности: {error}"
                    ) from error

            self.model = WhisperModel(
                path, device="cpu", compute_type="int8", local_files_only=True
            )

        segments, info = self.model.transcribe(audio, vad_filter=True)
        return " ".join(
            segment.text.strip() for segment in segments
            if segment.text.strip()
        )
