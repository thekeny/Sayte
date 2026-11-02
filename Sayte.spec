from PyInstaller.utils.hooks import collect_all, copy_metadata


datas = [("ui/*.ui", "ui"), ("images/*", "images")]
binaries = []
hiddenimports = ["ui.spinner", "ui.voice_wave"]
for package in ("faster_whisper", "ctranslate2", "av", "sounddevice"):
    packageData, packageBinaries, packageImports = collect_all(package)
    datas += packageData
    binaries += packageBinaries
    hiddenimports += packageImports
for package in ("faster-whisper", "huggingface-hub"):
    datas += copy_metadata(package, recursive=True)

a = Analysis(
    ["app.py"], pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=["PyQt5", "PySide2", "PySide6"]
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="Sayte",
    debug=False, bootloader_ignore_signals=False, strip=False,
    upx=False, console=False, icon="images/sayte-icon.png"
)
