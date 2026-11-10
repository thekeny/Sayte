import config


def get_builtin_presets():
    return [
        {"id": None, "name": name, "prompt": prompt}
        for name, prompt in config.AI_PRESETS
    ]
