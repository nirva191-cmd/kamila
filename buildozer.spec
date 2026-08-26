[app]

# (str) Title of your application
title = KAMILAIA

# (str) Package name
package.name = kmila

# (str) Package domain (needed for android packaging)
package.domain = org.test

# (str) Source file where the main.py is located
source.dir = .

# (list) Source files to include (let empty to include all files)
source.include_exts = py,png,jpg,jpeg,kv,atlas,json

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_dirs = tests,bin,venv,.git,.buildozer

# (str) Application versioning
version = 0.1

# (str) Icon of the application
icon.filename = %(source.dir)s/logo.png

# ============================================================
# DEPENDENCIAS
# ============================================================
requirements = python3,kivy,plyer

# ============================================================
# INTERFAZ
# ============================================================

orientation = portrait
fullscreen = 0

# ============================================================
# ANDROID
# ============================================================

# Permisos utilizados por la aplicación (incluyendo almacenamiento y audio/internet).
android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Versión de Android.
android.api = 33
android.minapi = 24

# Arquitecturas compatibles (permite arm64-v8a para celulares modernos)
android.archs = armeabi-v7a, arm64-v8a

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
