[app]

title = KAMILAIA
package.name = KMILA
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
source.exclude_dirs = tests,bin,venv,.git,.buildozer

version = 0.1

# ============================================================
# DEPENDENCIAS
# ============================================================
# Dependencias necesarias para Android.
#
# NO incluir:
# - pyttsx3
# - SpeechRecognition
# - requests
# - urllib3
# - certifi
# - openssl
#
# Las dos primeras son utilizadas por la aplicación en escritorio.
# urllib, json, base64, threading, etc. ya vienen con Python.
#
requirements = python3,kivy,plyer

# ============================================================
# INTERFAZ
# ============================================================

orientation = portrait
fullscreen = 0

# ============================================================
# ANDROID
# ============================================================

# Permisos utilizados por la aplicación.
android.permissions = INTERNET,RECORD_AUDIO

# Versión de Android.
android.api = 33
android.minapi = 24

# Usar armeabi-v7a para evitar errores de compilación cruzada en GitHub Actions.
android.archs = armeabi-v7a

# Aceptar automáticamente las licencias del Android SDK.
android.accept_sdk_license = True

# Mantener copia de seguridad de los datos de la aplicación.
android.allow_backup = True

# Generar APK en modo debug.
android.debug_artifact = apk

# ============================================================
# BUILDOZER
# ============================================================

[buildozer]

log_level = 2
warn_on_root
