from PyQt6.QtCore import QObject

from transcription.worker import TranscriptionWorker


class RecordingSession(QObject):
    def __init__(self, recorder, whisper, parent=None):
        super().__init__(parent)
        self.recorder = recorder
        self.whisper = whisper
        self.target = None
        self.worker = None

    def startRecording(self, target):
        if self.target is not None:
            raise RuntimeError("Дождитесь завершения текущей записи.")
        self.recorder.start()
        self.target = target

    def stopRecording(self, target):
        if self.target is not target or self.worker is not None:
            raise RuntimeError("Запись принадлежит другому окну.")
        try:
            return self.recorder.stop()
        finally:
            self.target = None

    def transcribe(self, target, audio, result, error, finished, status=None):
        if self.target is not None:
            raise RuntimeError("Дождитесь завершения текущей записи.")
        self.target = target
        self.worker = TranscriptionWorker(self.whisper, audio, self)
        self.worker.result.connect(result)
        self.worker.error.connect(error)
        if status is not None:
            self.worker.status.connect(status)
        self.worker.finished.connect(self.finishProcessing)
        self.worker.finished.connect(finished)
        self.worker.start()
        return self.worker

    def finishProcessing(self):
        self.worker.deleteLater()
        self.worker = None
        self.target = None
