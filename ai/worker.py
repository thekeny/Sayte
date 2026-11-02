from PyQt6.QtCore import QThread, pyqtSignal

import config
from ai.provider import Provider


class AiWorker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, profile, operation, prompt="", text="", parent=None):
        super().__init__(parent)
        self.profile = profile.copy()
        self.operation = operation
        self.prompt = prompt
        self.text = text

    def run(self):
        try:
            provider = Provider(self.profile)
            if self.operation == "models":
                result = provider.getModels()
            else:
                result = provider.processText(
                    self.profile["model"], self.prompt, self.text
                )
        except ValueError as error:
            self.error.emit(str(error))
        except Exception:
            self.error.emit(config.AI_ERRORS["request"])
        else:
            self.result.emit(result)
