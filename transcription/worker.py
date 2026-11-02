from PyQt6.QtCore import QThread, pyqtSignal


class TranscriptionWorker(QThread):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, whisper, audio, parent=None):
        super().__init__(parent)
        self.whisper = whisper
        self.audio = audio

    def run(self):
        try:
            text = self.whisper.transcribe(self.audio)
        except Exception as error:
            # Ошибки модели и её загрузки приходят из разных библиотек.
            self.error.emit(str(error))
        else:
            self.result.emit(text)
        finally:
            self.audio = None
