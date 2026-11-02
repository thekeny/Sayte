from PyQt6.QtCore import QThread, pyqtSignal


class TranscriptionWorker(QThread):
    status = pyqtSignal(str)
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, whisper, audio, parent=None):
        super().__init__(parent)
        self.whisper = whisper
        self.audio = audio

    def run(self):
        try:
            text = self.whisper.transcribe(self.audio, self.status.emit)
        except Exception as error:
            self.error.emit(str(error))
        else:
            self.result.emit(text)
        finally:
            self.audio = None
