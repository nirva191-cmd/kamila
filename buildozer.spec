[app]

title = Kamila AI
package.name = kamila
package.domain = org.kamila

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
source.exclude_dirs = tests,bin,venv,.git,.buildozer
version = 1.0

# Dependencias realmente necesarias para Android.
# No se incluyen pyttsx3 ni SpeechRecognition porque el código
# los usa únicamente en escritorio.
requirements = python3,kivy,plyer

orientation = portrait
fullscreen = 0

# Permisos utilizados por la aplicación.
android.permissions = INTERNET,RECORD_AUDIO

# Compatibilidad Android.
android.minapi = 24
android.api = 33

# Una sola arquitectura para reducir problemas y tiempo de compilación.
android.archs = arm64-v8a

android.allow_backup = True

# Generar APK para pruebas.
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
