import os

import config


class Whisper:
    def __init__(self):
        self.model = None

    def transcribe(self, audio, status=None):
        if audio.size == 0:
            return ""

        if self.model is None:
            os.environ["HF_HUB_DISABLE_XET"] = "1"
            os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
            from faster_whisper import WhisperModel
            from faster_whisper.utils import download_model
            from huggingface_hub.errors import LocalEntryNotFoundError

            cache = config.MODEL_CACHE_PATH
            try:
                path = download_model(
                    config.WHISPER_MODEL, cache_dir=cache,
                    local_files_only=True, use_auth_token=False
                )
            except LocalEntryNotFoundError:
                path = None

            files = ("model.bin", "config.json", "tokenizer.json")
            if path is None or not all(
                os.path.isfile(f"{path}/{name}") for name in files
            ):
                if status is not None:
                    status(config.MODEL_DOWNLOAD_TEXT)
                try:
                    path = download_model(
                        config.WHISPER_MODEL, cache_dir=cache,
                        use_auth_token=False
                    )
                except Exception as error:
                    raise RuntimeError(
                        "Не удалось скачать публичную модель Whisper. "
                        "Токен и аккаунт не нужны. Проверьте подключение "
                        "и доступ к huggingface.co, затем повторите запись.\n"
                        f"Подробности: {error}"
                    ) from error

            if status is not None:
                status(config.PROCESSING_TEXT)
            self.model = WhisperModel(
                path, device="cpu", compute_type="int8", local_files_only=True
            )

        _, _, probabilities = self.model.detect_language(audio=audio)
        languages = {language: probability for language, probability
                     in probabilities if language in ("ru", "en")}
        language = max(languages, key=languages.get) if languages else "ru"
        segments, info = self.model.transcribe(
            audio, language=language, vad_filter=True
        )
        return " ".join(
            segment.text.strip() for segment in segments
            if segment.text.strip()
        )
