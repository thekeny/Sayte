from PyQt6.QtGui import QIcon

import config


def profileIcon(profile):
    path = (
        config.OPENROUTER_ICON_PATH
        if profile["kind"] == "openrouter"
        else config.CPU_ICON_PATH
    )
    return QIcon(path)


def modelId(combo):
    index = combo.currentIndex()
    if index >= 0 and combo.currentText() == combo.itemText(index):
        return combo.itemData(index)
    return combo.currentText().strip()


def fillModels(combo, models, selected):
    combo.clear()
    for model in models:
        name, identifier = model["name"], model["id"]
        label = f"{name} ({identifier})" if name != identifier else identifier
        combo.addItem(label, identifier)
    index = combo.findData(selected)
    if index >= 0:
        combo.setCurrentIndex(index)
    else:
        combo.setCurrentIndex(-1)
        combo.setEditText(selected)
