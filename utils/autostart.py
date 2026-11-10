import os
import subprocess
import sys
import winreg

import config


def get_command():
    executable = sys.executable
    if getattr(sys, "frozen", False):
        args = [executable]
    else:
        executable = os.path.join(os.path.dirname(executable), "pythonw.exe")
        args = [executable, os.path.abspath("app.py")]
    return subprocess.list2cmdline(args + ["--start-in-tray"])


def get_autostart():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, config.AUTOSTART_KEY
        ) as key:
            return winreg.QueryValueEx(key, config.NAME)[0]
    except FileNotFoundError:
        return None


def set_autostart(command):
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, config.AUTOSTART_KEY
    ) as key:
        if command is not None:
            winreg.SetValueEx(key, config.NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, config.NAME)
            except FileNotFoundError:
                pass
