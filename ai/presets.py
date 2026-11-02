import config


def getBuiltinPresets():
    return [
        {"id": None, "name": name, "prompt": prompt}
        for name, prompt in config.AI_PRESETS
    ]
