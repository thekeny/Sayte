import ctypes
from ctypes.wintypes import MSG

from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication
from PyQt6.QtCore import QObject, pyqtSignal

import config


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, hotkey):
        super().__init__()
        self.hotkey = hotkey

    def nativeEventFilter(self, eventType, message):
        if eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = MSG.from_address(int(message))
            if msg.message == config.HOTKEY_MESSAGE and msg.wParam == self.hotkey.id:
                self.hotkey.activated.emit()
                return True, 0
        return False, 0


class Hotkey(QObject):
    activated = pyqtSignal()

    def __init__(self, shortcut):
        super().__init__()
        self.shortcut = shortcut
        self.id = config.HOTKEY_ID
        self.registered = False
        self.filter = HotkeyFilter(self)
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)

    def start(self):
        if self.registered:
            return
        parts = self.shortcut.lower().split("+")
        modifiers = config.HOTKEY_MODIFIERS
        flags = config.HOTKEY_NO_REPEAT
        for modifier in parts[:-1]:
            if modifier not in modifiers:
                raise ValueError("Неизвестный модификатор горячей клавиши")
            flags |= modifiers[modifier]
        key = parts[-1].upper()
        if len(key) != 1 or not key.isascii() or not key.isalnum():
            raise ValueError("Используйте букву A–Z или цифру 0–9")
        if not self.user32.RegisterHotKey(None, self.id, flags, ord(key)):
            raise ctypes.WinError(ctypes.get_last_error())
        QCoreApplication.instance().installNativeEventFilter(self.filter)
        self.registered = True

    def stop(self):
        if self.registered:
            self.user32.UnregisterHotKey(None, self.id)
            QCoreApplication.instance().removeNativeEventFilter(self.filter)
            self.registered = False
