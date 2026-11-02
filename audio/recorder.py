import numpy as np
import sounddevice as sd

import config


class Recorder:
    def __init__(self):
        self.stream = None
        self.frames = []
        self.error = ""
        self.level = 0.0

    def start(self):
        if self.stream is not None:
            return

        self.frames = []
        self.error = ""
        self.level = 0.0
        self.stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE, channels=1, dtype="float32",
            callback=self.recordAudio
        )
        try:
            self.stream.start()
        except (sd.PortAudioError, OSError):
            self.close()
            raise

    def recordAudio(self, data, frames, time, status):
        if status:
            self.error = str(status)
        self.frames.append(data[:, 0].copy())
        self.level = float(np.sqrt(np.mean(data[:, 0] ** 2)))

    def stop(self):
        try:
            if self.stream is not None:
                self.stream.stop()
            frames = self.frames
        finally:
            self.close()

        if self.error:
            raise RuntimeError(f"Ошибка потока микрофона: {self.error}")
        if not frames:
            return np.empty(0, dtype="float32")
        return np.concatenate(frames)

    def close(self):
        self.level = 0.0
        if self.stream is not None:
            stream = self.stream
            self.stream = None
            try:
                stream.close()
            finally:
                self.frames = []
