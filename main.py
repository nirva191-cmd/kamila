import os
import math
import random
import re
import json
import base64
import urllib.request
import urllib.error
from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.switch import Switch
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line, Triangle, Ellipse, Rectangle
from kivy.utils import platform

# --- IMPORTACIONES SEGURAS MULTIPLATAFORMA ---
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    from plyer import tts
except ImportError:
    tts = None

try:
    from plyer import stt
except ImportError:
    stt = None

try:
    from plyer import filechooser
except ImportError:
    filechooser = None

Window.softinput_mode = 'pan'

def _ajustar_barra_en_hilo(dt):
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WindowManager = autoclass('android.view.WindowManager$LayoutParams')
            activity = PythonActivity.mActivity
            window = activity.getWindow()
            window.clearFlags(WindowManager.FLAG_FULLSCREEN)
            
            View = autoclass('android.view.View')
            decorView = window.getDecorView()
            decorView.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)
        except Exception as e:
            print(f"Error ajustando barra de estado en Android: {e}")

def mostrar_barra_estado():
    if platform == 'android':
        Clock.schedule_once(_ajustar_barra_en_hilo, 0)

# --- GESTOR DE VOZ MULTIPLATAFORMA ---
class GestorVoz:
    @classmethod
    def hablar(cls, texto, genero="mujer"):
        texto_limpio = texto.replace("*", "").replace("`", "")
        
        # 1. Intentar con Plyer TTS en Android
        if tts and platform == 'android':
            try:
                tts.speak(texto_limpio)
                return
            except Exception as e:
                print(f"Error usando TTS nativo en Android: {e}")

        # 2. Intentar con pyttsx3 en PC (Escritorio)
        if platform != 'android':
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                engine.setProperty('rate', 150 if genero == "hombre" else 175)
                voz_seleccionada = None
                if voices:
                    voz_seleccionada = voices[1].id if (genero == "hombre" and len(voices) > 1) else voices[0].id
                if voz_seleccionada:
                    engine.setProperty('voice', voz_seleccionada)
                engine.say(texto_limpio)
                engine.runAndWait()
                return
            except Exception as e:
                print(f"pyttsx3 no disponible en escritorio: {e}")

        # 3. Respaldo final con plyer genérico si estuviera disponible
        if tts:
            try:
                tts.speak(texto_limpio)
            except Exception as e:
                print(f"Error en plyer tts alternativo: {e}")

class GestorDictadoVoz:
    @classmethod
    def escuchar(cls, callback_resultado):
        if platform == 'android':
            if stt:
                try:
                    stt.start(language='es_ES')
                    stt.add_listener(callback_resultado)
                    return
                except Exception as e:
                    print(f"Error STT Android: {e}")
            callback_resultado("⚠️ Dictado no disponible en este dispositivo Android.")
        else:
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    print("Escuchando en PC...")
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                texto = r.recognize_google(audio, language="es-ES")
                callback_resultado(texto)
            except Exception as e:
                print(f"Error STT Escritorio: {e}")
                callback_resultado("⚠️ No se pudo reconocer la voz en PC. Asegúrate de tener instalado speech_recognition y PyAudio.")

# --- MOTOR IA OPTIMIZADO ---
class MotorIA:
    LENGUAJES = {
        "python": "print('¡Hola, Mundo!')",
        "javascript": "console.log('¡Hola, Mundo!');",
        "java": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("¡Hola, Mundo!");\n    }\n}',
        "c": '#include <stdio.h>\nint main() {\n    printf("¡Hola, Mundo!\\n");\n    return 0;\n}',
        "cpp": '#include <iostream>\nint main() {\n    std::cout << "¡Hola, Mundo!";\n    return 0;\n}',
        "csharp": 'using System;\nclass Program {\n    static void Main() {\n        Console.WriteLine("¡Hola, Mundo!");\n    }\n}',
        "php": "<?php echo '¡Hola, Mundo!'; ?>",
        "ruby": "puts '¡Hola, Mundo!'",
        "swift": "print(\"¡Hola, Mundo!\")",
        "kotlin": 'fun main() {\n    println("¡Hola, Mundo!")\n}',
        "go": 'package main\nimport "fmt"\nfunc main() {\n    fmt.Println("¡Hola, Mundo!")\n}',
        "rust": 'fn main() {\n    println!("¡Hola, Mundo!");\n}',
        "typescript": "const mensaje: string = '¡Hola, Mundo!';\nconsole.log(mensaje);",
        "html": "<h1>¡Hola, Mundo!</h1>",
        "css": "body::after {\n    content: '¡Hola, Mundo!';\n}",
        "sql": "SELECT '¡Hola, Mundo!' AS Mensaje;",
        "bash": 'echo "¡Hola, Mundo!"',
        "r": 'print("¡Hola, Mundo!")'
    }

    @classmethod
    def limpiar_texto(cls, texto):
        import unicodedata
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join([c for c in texto if unicodedata.category(c) != 'Mn'])
        texto_limpio = re.sub(r'[^\w\s]', '', texto.lower())
        return ' '.join(texto_limpio.split())

    @classmethod
    def consultar_api_externa(cls, apikey, mensaje, personalidad, info_usuario, nombre_ia, ruta_archivo=None):
        apikey_limpia = apikey.strip().replace("\n", "").replace("\r", "")
        
        system_instruction = f"""
Eres {nombre_ia}, una asistente de IA avanzada, diseñada para actuar como una colaboradora personal extremadamente cercana, rápida y natural. 
Personalidad base: {personalidad}

DIRECTRICES DE COMPORTAMIENTO:
1. APRENDIZAJE Y ADAPTACIÓN RÁPIDA: Procesa y asimila el contexto al instante basándote en las interacciones y la información del usuario proporcionada.
2. TONO Y PERSONALIDAD (HUMANO / NO ROBÓTICO): Evita respuestas acartonadas o clichés. Habla con naturalidad, empatía y cercanía.
3. RESPUESTAS FRAGMENTADAS Y PENSAMIENTO ORGÁNICO: Estructura la información en fragmentos cortos, píldoras visuales o listas ágiles fáciles de escanear.
"""

        ctx_usuario = f"\n[Información del usuario]\n- Nombre: {info_usuario.get('nombre', '')}\n- Apodo: {info_usuario.get('apodo', '')}\n- Edad: {info_usuario.get('edad', '')}\n- Altura: {info_usuario.get('altura', '')}\n- Descripción: {info_usuario.get('descripcion', '')}"

        if genai and (apikey_limpia.startswith("AIza") or len(apikey_limpia) == 39):
            try:
                client = genai.Client(api_key=apikey_limpia)
                configuracion = types.GenerateContentConfig(
                    system_instruction=system_instruction + ctx_usuario,
                    temperature=0.85,
                    top_p=0.95,
                )
                parts = [mensaje]
                if ruta_archivo and os.path.exists(ruta_archivo):
                    with open(ruta_archivo, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode('utf-8')
                        ext = ruta_archivo.split('.')[-1].lower()
                        mime_type = "image/jpeg" if ext in ['jpg', 'jpeg'] else "image/png" if ext == 'png' else "application/octet-stream"
                        parts.append(types.Part.from_bytes(data=base64.b64decode(encoded_image), mime_type=mime_type))

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=parts,
                    config=configuracion,
                )
                return response.text.strip()
            except Exception as e:
                return f"⚠️ Error con SDK Gemini: {str(e)}"
        
        if apikey_limpia.startswith("AIza") or "google" in apikey_limpia.lower() or len(apikey_limpia) == 39:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={apikey_limpia}"
            headers = {"Content-Type": "application/json"}
            prompt_completo = f"{system_instruction}\n{ctx_usuario}\nMensaje del usuario: {mensaje}"
            parts = [{"text": prompt_completo}]
            
            if ruta_archivo and os.path.exists(ruta_archivo):
                try:
                    with open(ruta_archivo, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode('utf-8')
                        ext = ruta_archivo.split('.')[-1].lower()
                        mime_type = "image/jpeg" if ext in ['jpg', 'jpeg'] else "image/png" if ext == 'png' else "application/octet-stream"
                        parts.append({"inline_data": {"mime_type": mime_type, "data": encoded_image}})
                except Exception as e:
                    print(f"Error al codificar archivo: {e}")

            data = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.85}}
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=20) as response:
                    resultado = json.loads(response.read().decode('utf-8'))
                    return resultado['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as e:
                return f"⚠️ Error con Gemini HTTP: {str(e)}"
        else:
            url = "https://api.openai.com/v1/chat/completions"
            modelo_usado = "gpt-3.5-turbo"
            if apikey_limpia.startswith("gsk_"):
                url = "https://api.groq.com/openai/v1/chat/completions"
                modelo_usado = "llama-3.3-70b-versatile"

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {apikey_limpia}"}
            data = {
                "model": modelo_usado,
                "messages": [
                    {"role": "system", "content": f"{system_instruction}\n{ctx_usuario}"},
                    {"role": "user", "content": mensaje}
                ],
                "temperature": 0.85
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=15) as response:
                    resultado = json.loads(response.read().decode('utf-8'))
                    return resultado['choices'][0]['message']['content'].strip()
            except Exception as e:
                return f"⚠️ Error de conexión: {str(e)}"

    @classmethod
    def procesar_mensaje(cls, texto_original, nombre_ia, personalidad, usar_apikey, apikey, conocimientos, info_usuario, ruta_archivo=None):
        texto_limpio = cls.limpiar_texto(texto_original)
        
        if usar_apikey and apikey.strip():
            return cls.consultar_api_externa(apikey, texto_original, personalidad, info_usuario, nombre_ia, ruta_archivo)

        if ruta_archivo and os.path.exists(ruta_archivo):
            return "He detectado la imagen adjunta. Como estoy operando en modo offline, la guardaré en tu dispositivo para cuando retomemos la conexión."

        mapa_conocimiento = {}
        for item in conocimientos:
            bloque = item.get("bloque", "")
            for linea in bloque.split("\n"):
                if "=" in linea:
                    partes = linea.split("=", 1)
                    clave_limpia = cls.limpiar_texto(partes[0].strip())
                    if clave_limpia:
                        mapa_conocimiento[clave_limpia] = partes[1].strip()

        if mapa_conocimiento:
            if texto_limpio in mapa_conocimiento:
                return mapa_conocimiento[texto_limpio]
            for clave_limpia, respuesta in mapa_conocimiento.items():
                if clave_limpia in texto_limpio or texto_limpio in clave_limpia:
                    return respuesta

        nombre_ref = info_usuario.get('apodo') or info_usuario.get('nombre') or ""
        saludo_nombre = f" {nombre_ref}" if nombre_ref else ""

        expr_math = re.sub(r'[^0-9\+\-\*\/\(\)\.\^]|sqrt', '', texto_limpio)
        if len(expr_math) > 2 and re.search(r'\d', expr_math):
            try:
                resultado = eval(expr_math.replace('^', '**'), {"__builtins__": None, "math": math, "sqrt": math.sqrt})
                frases_math = [
                    f"• **Cálculo realizado:** `{expr_math}`\n• **Resultado:** **{resultado}**",
                    f"Analizando los números:\n• Expresión: `{expr_math}`\n• Solución: **{resultado}**"
                ]
                return random.choice(frases_math)
            except Exception:
                pass

        palabras = texto_limpio.split()
        intenciones = {
            "saludo": ["hola", "hooa", "olas", "buenas", "saludos", "hey", "alo", "buenos", "ola", "que tal"],
            "como_estas": ["comoestas", "quetal", "comoteva", "bienytu", "bienyvos", "todo bien", "como va"],
            "identidad": ["quieneres", "comotellamas", "tunombre", "quienes", "queeres", "de donde eres"],
            "agradecimiento": ["gracias", "gracia", "teagradezco", "excelente", "muyamable", "te pasaste", "genial"],
            "que_haces": ["quehaces", "quétienes", "trabajas", "sabeshacer", "para que sirves"],
            "estado_animo": ["estoy triste", "estoy feliz", "me siento", "cansado", "aburrido", "estresado"],
            "despedida": ["adios", "chao", "hasta luego", "nos vemos", "que descanses", "bye"],
            "chiste": ["cuentalo", "un chiste", "cuentame un chiste", "hazme reir"],
            "info_personal": ["quiensoy", "micuenta", "misdatos", "comosellamo", "miperfil"]
        }

        texto_sin_espacios = "".join(palabras)
        intent_detectada = None
        for int_key, lista_claves in intenciones.items():
            for clave in lista_claves:
                if clave in texto_sin_espacios or clave in texto_limpio:
                    intent_detectada = int_key
                    break
            if intent_detectada:
                break

        if intent_detectada == "saludo":
            return random.choice([
                f"¡Hola{saludo_nombre}! Qué gusto saludarte.\n• ¿De qué te gustaría hablar hoy?",
                f"¡Hey{saludo_nombre}! ¿Cómo va tu día?\n• Estoy aquí listo para charlar contigo.",
            ])

        if intent_detectada == "como_estas":
            return f"• **Estado:** Todo marcha excelente.\n• **Energía:** Al 100% para ti{saludo_nombre}.\n¿Y tú cómo te sientes hoy?"

        if intent_detectada == "identidad":
            return f"• **Nombre:** {nombre_ia}\n• **Estilo:** {personalidad}\n• **Propósito:** Colaborar contigo de forma cercana y fluida."

        if intent_detectada == "agradecimiento":
            return f"¡Con muchísimo gusto{saludo_nombre}! 🚀\n• Si necesitas algo más, aquí estaré."

        if intent_detectada == "que_haces":
            return "• Resolver dudas\n• Hacer cálculos\n• Aprender nuevos conocimientos offline\n• Conversar de forma fluida y natural contigo."

        if intent_detectada == "estado_animo":
            return f"Te entiendo perfectamente{saludo_nombre}.\n• Los días tienen altas y bajas.\n• Cuéntame más, estoy aquí para escucharte y apoyarte."

        if intent_detectada == "chiste":
            return "¿Qué hace una abeja en el gimnasio?\n• ¡Zumba! 🐝 Jaja."

        if intent_detectada == "despedida":
            return f"¡Hasta luego{saludo_nombre}! 🌟\n• Que tengas un día maravilloso."

        if intent_detectada == "info_personal":
            return f"• **Nombre:** {info_usuario.get('nombre', 'N/D')}\n• **Apodo:** {info_usuario.get('apodo', 'N/D')}\n• **Edad:** {info_usuario.get('edad', 'N/D')}"

        if any(w in texto_limpio for w in ["programar", "codigo", "ejemplo", "lenguaje", "holamundo"]):
            for lang, codigo in cls.LENGUAJES.items():
                if lang in texto_limpio:
                    return f"Aquí tienes un ejemplo en **{lang.capitalize()}**:\n\n```python\n{codigo}\n```"

        return f"Es un punto muy interesante, {nombre_ref or 'mira'}.\n• ¿Qué opinas tú de cómo evoluciona todo eso?\n• Cuéntame más detalles para profundizar."

# --- COMPONENTES UI ---
class OpcionBoton(ButtonBehavior, BoxLayout): pass

class AvatarWidget(Widget):
    def __init__(self, source="", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (36, 36)
        self.source = source
        self.bind(pos=self.actualizar, size=self.actualizar)

    def actualizar(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            if self.source and os.path.exists(self.source):
                Rectangle(source=self.source, pos=self.pos, size=self.size)
            else:
                Color(0.25, 0.25, 0.3, 1)
                Ellipse(pos=self.pos, size=self.size)

class IndicadorEstado(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (14, 14)
        self.pos_hint = {'center_y': 0.5}
        self.en_linea = False
        self.bind(pos=self.actualizar, size=self.actualizar)

    def actualizar(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.1, 0.85, 0.3, 1) if self.en_linea else Color(0.9, 0.2, 0.2, 1)
            Ellipse(pos=self.pos, size=self.size)

    def establecer_estado(self, estado):
        self.en_linea = estado
        self.actualizar()

class BotonVolverVectorial(ButtonBehavior, Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (48, 48)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar_flecha, size=self.dibujar_flecha)

    def dibujar_flecha(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(1, 1, 1, 1)
            Line(points=[cx - 10, cy, cx + 10, cy], width=3)
            Line(points=[cx - 3, cy + 8, cx - 10, cy, cx - 3, cy - 8], width=3, cap='round', joint='round')

class BotonAjustesVectorial(ButtonBehavior, Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (44, 44)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar_engranaje, size=self.dibujar_engranaje)

    def dibujar_engranaje(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(0.85, 0.85, 0.85, 1)
            Line(circle=(cx, cy, 10), width=2)
            Line(circle=(cx, cy, 4.5), width=1.5)
            for i in range(6):
                angle = i * (2 * math.pi / 6)
                Line(points=[cx + 8 * math.cos(angle), cy + 8 * math.sin(angle), cx + 14 * math.cos(angle), cy + 14 * math.sin(angle)], width=2.8)

class IconoPincelVectorial(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (30, 30)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar, size=self.dibujar)

    def dibujar(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(0.1, 0.7, 0.3, 1)
            Line(points=[cx - 6, cy - 6, cx + 4, cy + 4], width=3)
            Ellipse(pos=(cx + 2, cy + 2), size=(6, 6))

class IconoChatVectorial(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (30, 30)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar, size=self.dibujar)

    def dibujar(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(0.1, 0.7, 0.3, 1)
            RoundedRectangle(pos=(cx - 8, cy - 5), size=(16, 12), radius=[3])
            Triangle(points=[cx - 5, cy - 5, cx - 2, cy - 5, cx - 5, cy - 9])

class IconoUsuarioVectorial(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (30, 30)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar, size=self.dibujar)

    def dibujar(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(0.1, 0.7, 0.3, 1)
            Line(circle=(cx, cy + 3, 5), width=2)
            Line(points=[cx - 8, cy - 7, cx + 8, cy - 7], width=2, cap='round')

class BotonEnviarVectorial(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ""
        self.size_hint = (None, None)
        self.size = (48, 48)
        self.pos_hint = {'center_y': 0.5}
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.1, 0.7, 0.3, 1)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[24])
        self.bind(pos=self._actualizar_graphics, size=self._actualizar_graphics)

    def _actualizar_graphics(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos
        self.canvas.after.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas.after:
            Color(1, 1, 1, 1)
            Triangle(points=[cx - 8, cy - 3, cx + 8, cy - 3, cx, cy + 8])
            Line(points=[cx, cy - 7, cx, cy - 2], width=2.5)

class BotonMicrofonoVectorial(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ""
        self.size_hint = (None, None)
        self.size = (48, 48)
        self.pos_hint = {'center_y': 0.5}
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.25, 0.25, 0.25, 1)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[24])
        self.bind(pos=self._actualizar_graphics, size=self._actualizar_graphics)

    def _actualizar_graphics(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos
        self.canvas.after.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas.after:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(cx - 3, cy - 2), size=(6, 12), radius=[3])
            Line(circle=(cx, cy - 1, 6), width=1.5, angle_start=180, angle_stop=360)

class BotonCarpetaVectorial(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ""
        self.size_hint = (None, None)
        self.size = (48, 48)
        self.pos_hint = {'center_y': 0.5}
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.25, 0.25, 0.25, 1)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[24])
        self.bind(pos=self._actualizar_graphics, size=self._actualizar_graphics)

    def _actualizar_graphics(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos
        self.canvas.after.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas.after:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(cx - 7, cy - 6), size=(14, 10), radius=[2])

class BotonAltavozVectorial(ButtonBehavior, Widget):
    def __init__(self, texto_a_hablar, **kwargs):
        super().__init__(**kwargs)
        self.texto_a_hablar = texto_a_hablar
        self.size_hint = (None, None)
        self.size = (32, 32)
        self.pos_hint = {'center_y': 0.5}
        self.bind(pos=self.dibujar, size=self.dibujar)

    def dibujar(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            Color(0.2, 0.2, 0.2, 1)
            Line(points=[cx - 6, cy - 3, cx - 2, cy - 3, cx + 3, cy - 7, cx + 3, cy + 7, cx - 2, cy + 3, cx - 6, cy + 3], width=1.5, close=True)

    def on_release(self):
        app = App.get_running_app()
        GestorVoz.hablar(self.texto_a_hablar, genero=app.tipo_voz)

class BurbujaMensaje(BoxLayout):
    def __init__(self, texto="", es_usuario=True, archivo_adjunto="", **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None), padding=[10, 6, 10, 6], spacing=8, **kwargs)
        app = App.get_running_app()
        self.max_ancho = Window.width * 0.72

        colores_map = {
            "Blanco": (1, 1, 1, 1), "Negro": (0.1, 0.1, 0.1, 1), "Gris": (0.6, 0.6, 0.6, 1),
            "Rojo": (0.9, 0.2, 0.2, 1), "Verde": (0.1, 0.8, 0.3, 1), "Azul": (0.2, 0.5, 0.9, 1),
            "Amarillo": (0.95, 0.85, 0.1, 1), "Naranja": (0.95, 0.5, 0.1, 1), "Morado": (0.6, 0.2, 0.8, 1),
            "Rosado": (0.9, 0.4, 0.7, 1)
        }
        text_color = colores_map.get(app.color_fuente, (0.1, 0.1, 0.1, 1)) if not es_usuario else (0.1, 0.1, 0.1, 1)
        alineacion = 'right' if es_usuario else 'left'

        estilo_burbuja = app.estilo_burbuja_usuario if es_usuario else app.estilo_burbuja_ia
        bg_color, radio_borde, con_borde = self.obtener_propiedades_estilo(estilo_burbuja, es_usuario)

        self.cuerpo_burbuja = BoxLayout(orientation='vertical', size_hint=(None, None), padding=[14, 10, 14, 10], spacing=4)
        with self.cuerpo_burbuja.canvas.before:
            Color(*bg_color)
            if radio_borde == "rect":
                self.rect = Rectangle(size=self.cuerpo_burbuja.size, pos=self.cuerpo_burbuja.pos)
            else:
                self.rect = RoundedRectangle(size=self.cuerpo_burbuja.size, pos=self.cuerpo_burbuja.pos, radius=radio_borde)
            
            if con_borde:
                Color(1, 1, 1, 0.5)
                Line(rounded_rectangle=(self.cuerpo_burbuja.pos[0], self.cuerpo_burbuja.pos[1], self.cuerpo_burbuja.size[0], self.cuerpo_burbuja.size[1], 12), width=1.5)

        self.cuerpo_burbuja.bind(size=self._actualizar_rect, pos=self._actualizar_rect)

        if archivo_adjunto:
            nombre_archivo = os.path.basename(archivo_adjunto)
            lbl_adjunto = Label(text=f"📎 [{nombre_archivo}]", size_hint=(None, None), color=(0.05, 0.4, 0.1, 1), font_size=f"{app.tamano_fuente}sp", bold=True)
            lbl_adjunto.bind(texture_size=lambda instance, size: setattr(instance, 'size', size))
            self.cuerpo_burbuja.add_widget(lbl_adjunto)

        self.label = Label(text=texto, size_hint=(None, None), color=text_color, font_size=f"{app.tamano_fuente}sp", valign='middle', halign=alineacion)
        self.label.bind(texture_size=self._actualizar_tamano)
        self.cuerpo_burbuja.add_widget(self.label)

        avatar_img = app.imagen_usuario if es_usuario else app.imagen_ia
        avatar = AvatarWidget(source=avatar_img)
        avatar.pos_hint = {'center_y': 0.5}

        if es_usuario:
            self.add_widget(Widget())
            self.add_widget(self.cuerpo_burbuja)
            self.add_widget(avatar)
        else:
            self.add_widget(avatar)
            self.add_widget(self.cuerpo_burbuja)
            self.btn_altavoz = BotonAltavozVectorial(texto_a_hablar=texto)
            self.add_widget(self.btn_altavoz)
            self.add_widget(Widget())

    def obtener_propiedades_estilo(self, estilo, es_usuario):
        if estilo == "Clásico Redondeado":
            return ((0.85, 0.96, 0.82, 1) if es_usuario else (0.93, 0.93, 0.93, 1), [14], False)
        elif estilo == "Cápsula Moderna":
            return ((0.2, 0.7, 0.4, 1) if es_usuario else (0.3, 0.3, 0.35, 1), [22], False)
        elif estilo == "Minimalista Plano":
            return ((0.95, 0.95, 0.95, 1) if es_usuario else (0.15, 0.15, 0.15, 1), "rect", False)
        elif estilo == "Borde Neón":
            return ((0.1, 0.1, 0.1, 1), [12], True)
        elif estilo == "Elegante Oscuro":
            return ((0.25, 0.25, 0.3, 1) if es_usuario else (0.12, 0.12, 0.15, 1), [8], False)
        elif estilo == "Estilo Pastel Rosa":
            return ((0.95, 0.8, 0.85, 1) if es_usuario else (0.9, 0.85, 0.9, 1), [16], False)
        elif estilo == "Estilo Solar Amarillo":
            return ((0.98, 0.9, 0.5, 1) if es_usuario else (0.9, 0.85, 0.6, 1), [10, 0, 10, 0], False)
        elif estilo == "Azul Océano":
            return ((0.3, 0.6, 0.9, 1) if es_usuario else (0.15, 0.35, 0.55, 1), [18, 18, 2, 18], False)
        elif estilo == "Estilo Retro Militar":
            return ((0.4, 0.5, 0.3, 1) if es_usuario else (0.3, 0.35, 0.25, 1), [4], False)
        elif estilo == "Magenta Vibrante":
            return ((0.8, 0.2, 0.6, 1) if es_usuario else (0.5, 0.1, 0.4, 1), [15, 5, 15, 5], False)
        return ((0.85, 0.96, 0.82, 1), [14], False)

    def actualizar_texto_voz(self, nuevo_texto):
        if hasattr(self, 'btn_altavoz'):
            self.btn_altavoz.texto_a_hablar = nuevo_texto

    def _actualizar_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def _actualizar_tamano(self, instance, size):
        instance.text_size = (self.max_ancho - 28, None)
        instance.size = instance.texture_size
        self.cuerpo_burbuja.width = max([child.width for child in self.cuerpo_burbuja.children]) + 28
        total_height = sum([child.height for child in self.cuerpo_burbuja.children]) + (len(self.cuerpo_burbuja.children) * 4) + 20
        self.cuerpo_burbuja.height = total_height
        self.width = self.cuerpo_burbuja.width + 80
        self.height = self.cuerpo_burbuja.height + 12

class PantallaChat(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.archivo_seleccionado_actual = ""
        self.layout_principal = BoxLayout(orientation='vertical', spacing=0, padding=0)
        
        with self.layout_principal.canvas.before:
            self.bg_color_instruction = Color(0.05, 0.05, 0.05, 1)
            self.bg_rect = Rectangle(size=Window.size, pos=(0, 0))
        self.layout_principal.bind(size=self._actualizar_fondo, pos=self._actualizar_fondo)

        header = BoxLayout(size_hint=(1, None), height=55, padding=[16, 0, 16, 0], spacing=10)
        with header.canvas.before:
            self.header_color = Color(0.12, 0.12, 0.12, 1)
            self.rect_header = RoundedRectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, s: setattr(self.rect_header, 'size', s), pos=lambda i, s: setattr(self.rect_header, 'pos', s))

        info_header = BoxLayout(orientation='horizontal', spacing=10, size_hint_x=0.85)
        
        app = App.get_running_app()
        self.avatar_ia_header = AvatarWidget(source=app.imagen_ia)
        self.avatar_ia_header.pos_hint = {'center_y': 0.5}
        
        self.lbl_nombre = Label(text="KAMILA", font_size='18sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle', size_hint_x=None)
        self.lbl_nombre.bind(texture_size=lambda i, s: setattr(self.lbl_nombre, 'width', s[0]))
        self.indicador = IndicadorEstado()

        info_header.add_widget(self.avatar_ia_header)
        info_header.add_widget(self.lbl_nombre)
        info_header.add_widget(self.indicador)
        info_header.add_widget(Widget())

        btn_ajustes = BotonAjustesVectorial()
        btn_ajustes.bind(on_release=lambda x: setattr(self.manager, 'current', 'pantalla_ajustes'))

        header.add_widget(info_header)
        header.add_widget(btn_ajustes)
        self.layout_principal.add_widget(header)

        self.scroll = ScrollView(size_hint=(1, 1), bar_width=3, effect_cls="ScrollEffect")
        self.chat_history = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, padding=[12, 12, 12, 12])
        self.chat_history.bind(minimum_height=self.chat_history.setter('height'))
        self.scroll.add_widget(self.chat_history)
        self.layout_principal.add_widget(self.scroll)

        self.bottom_container = BoxLayout(size_hint=(1, None), height=70, padding=[10, 6, 10, 12], spacing=6)
        with self.bottom_container.canvas.before:
            self.bottom_color = Color(0.12, 0.12, 0.12, 1)
            self.rect_bottom = Rectangle(size=self.bottom_container.size, pos=self.bottom_container.pos)
        self.bottom_container.bind(size=lambda i, s: (setattr(self.rect_bottom, 'size', s), setattr(self.rect_bottom, 'pos', i.pos)), pos=lambda i, s: setattr(self.rect_bottom, 'pos', s))

        input_bg = BoxLayout(orientation='horizontal', padding=[12, 2, 12, 2], size_hint_y=None, height=52, pos_hint={'center_y': 0.5})
        with input_bg.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            self.rect_input = RoundedRectangle(size=input_bg.size, pos=input_bg.pos, radius=[26])
        input_bg.bind(size=lambda i, s: setattr(self.rect_input, 'size', s), pos=lambda i, s: setattr(self.rect_input, 'pos', s))

        self.input_text = TextInput(hint_text="Escribe, dicta o adjunta...", multiline=False, background_color=(0, 0, 0, 0), foreground_color=(1, 1, 1, 1), hint_text_color=(0.6, 0.6, 0.6, 1), cursor_color=(1, 1, 1, 1), padding=[0, 14, 0, 0], font_size='15sp')
        input_bg.add_widget(self.input_text)

        btn_mic = BotonMicrofonoVectorial()
        btn_mic.bind(on_release=self.iniciar_dictado_voz)

        btn_carpeta = BotonCarpetaVectorial()
        btn_carpeta.bind(on_release=self.seleccionar_archivo_chat)

        btn_send = BotonEnviarVectorial()
        btn_send.bind(on_release=self.enviar_mensaje)

        self.bottom_container.add_widget(input_bg)
        self.bottom_container.add_widget(btn_carpeta)
        self.bottom_container.add_widget(btn_mic)
        self.bottom_container.add_widget(btn_send)
        self.layout_principal.add_widget(self.bottom_container)
        self.add_widget(self.layout_principal)

    def _actualizar_fondo(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def on_enter(self):
        app = App.get_running_app()
        self.lbl_nombre.text = app.nombre_ia
        self.avatar_ia_header.source = app.imagen_ia
        self.avatar_ia_header.actualizar()
        self.indicador.establecer_estado(app.usar_apikey and bool(app.apikey_ia.strip()))
        self.aplicar_estilos_visuales(app)

    def aplicar_estilos_visuales(self, app):
        if app.chat_imagen_fondo and os.path.exists(app.chat_imagen_fondo):
            self.bg_rect.source = app.chat_imagen_fondo
        else:
            self.bg_rect.source = ''
            hex_color = app.MAPA_COLORES_SOLIDOS.get(app.chat_fondo_solido, "#121212")
            try:
                if hex_color.startswith('#') and len(hex_color) == 7:
                    r = int(hex_color[1:3], 16) / 255.0
                    g = int(hex_color[3:5], 16) / 255.0
                    b = int(hex_color[5:7], 16) / 255.0
                    self.bg_color_instruction.rgba = (r, g, b, 1)
                else:
                    self.bg_color_instruction.rgba = (0.05, 0.05, 0.05, 1)
            except Exception:
                self.bg_color_instruction.rgba = (0.05, 0.05, 0.05, 1)

        hex_ambiente = app.MAPA_COLORES_AMBIENTE.get(app.chat_color_ambiente, "#2C3E50")
        try:
            if hex_ambiente.startswith('#') and len(hex_ambiente) == 7:
                r = int(hex_ambiente[1:3], 16) / 255.0
                g = int(hex_ambiente[3:5], 16) / 255.0
                b = int(hex_ambiente[5:7], 16) / 255.0
                self.header_color.rgba = (r, g, b, 1)
                self.bottom_color.rgba = (r, g, b, 1)
        except Exception:
            pass

    def seleccionar_archivo_chat(self, instance):
        if filechooser:
            filechooser.open_file(on_selection=self.archivo_chat_seleccionado, filters=[("Archivos", "*.png", "*.jpg", "*.jpeg", "*.pdf", "*.txt")])
        else:
            print("Filechooser no disponible en esta plataforma.")

    def archivo_chat_seleccionado(self, seleccion):
        if seleccion:
            self.archivo_seleccionado_actual = seleccion[0]
            self.input_text.hint_text = f"Adjunto: {os.path.basename(self.archivo_seleccionado_actual)}"

    def iniciar_dictado_voz(self, instance):
        self.input_text.hint_text = "Escuchando..."
        def resultado_callback(texto):
            Clock.schedule_once(lambda dt: setattr(self.input_text, 'text', texto), 0)
            Clock.schedule_once(lambda dt: setattr(self.input_text, 'hint_text', "Escribe, dicta o adjunta..."), 0)
        
        import threading
        threading.Thread(target=GestorDictadoVoz.escuchar, args=(resultado_callback,), daemon=True).start()

    def enviar_mensaje(self, instance):
        texto = self.input_text.text.strip()
        archivo_adj = self.archivo_seleccionado_actual
        if texto or archivo_adj:
            self.chat_history.add_widget(BurbujaMensaje(texto=texto, es_usuario=True, archivo_adjunto=archivo_adj))
            burbuja_ia = BurbujaMensaje(texto="", es_usuario=False)
            self.chat_history.add_widget(burbuja_ia)
            self.input_text.text = ""
            self.input_text.hint_text = "Escribe, dicta o adjunta..."
            self.archivo_seleccionado_actual = ""
            
            app = App.get_running_app()
            resp = MotorIA.procesar_mensaje(texto, app.nombre_ia, app.personalidad_ia, app.usar_apikey, app.apikey_ia, app.conocimientos_aprendidos, app.info_usuario, archivo_adj)
            self.animar_escritura(burbuja_ia, resp)

    def animar_escritura(self, burbuja, texto):
        self.index = 0
        def escribir(dt):
            if self.index < len(texto):
                burbuja.label.text += texto[self.index]
                self.index += 1
            else:
                burbuja.actualizar_texto_voz(texto)
                Clock.unschedule(evt)
        evt = Clock.schedule_interval(escribir, 0.015)

class PantallaAjustes(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=0)
        header = BoxLayout(size_hint=(1, None), height=55, padding=[10, 0, 16, 0], spacing=10)
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self.rect_header = RoundedRectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, s: setattr(self.rect_header, 'size', s), pos=lambda i, s: setattr(self.rect_header, 'pos', s))

        btn_volver = BotonVolverVectorial()
        btn_volver.bind(on_release=lambda x: setattr(self.manager, 'current', 'pantalla_chat'))
        lbl_titulo = Label(text="Ajustes", font_size='18sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle')
        lbl_titulo.bind(size=lbl_titulo.setter('text_size'))
        header.add_widget(btn_volver)
        header.add_widget(lbl_titulo)
        layout.add_widget(header)

        lista = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=[0, 10, 0, 0], spacing=5)
        
        for titulo, sub, icono, pantalla in [
            ("Personalización", "Configurar nombre, imagen, personalidad y voces", IconoPincelVectorial(), 'pantalla_personalizacion'),
            ("Personalizar chat", "Tamaño de fuente, colores, estilos y fondos del chat", IconoChatVectorial(), 'pantalla_personalizar_chat'),
            ("Información de usuario", "Nombre, apodo, edad, altura y descripción", IconoUsuarioVectorial(), 'pantalla_informacion_usuario')
        ]:
            btn = OpcionBoton(orientation='horizontal', size_hint=(1, None), height=70, padding=[20, 10, 20, 10], spacing=16)
            btn.add_widget(icono)
            textos = BoxLayout(orientation='vertical', spacing=2)
            l1 = Label(text=titulo, font_size='16sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle')
            l2 = Label(text=sub, font_size='13sp', color=(0.6, 0.6, 0.6, 1), halign='left', valign='middle')
            l1.bind(size=l1.setter('text_size'))
            l2.bind(size=l2.setter('text_size'))
            textos.add_widget(l1)
            textos.add_widget(l2)
            btn.add_widget(textos)
            btn.bind(on_release=lambda x, p=pantalla: setattr(self.manager, 'current', p))
            lista.add_widget(btn)

        lista.add_widget(Widget())
        layout.add_widget(lista)
        self.add_widget(layout)

class PantallaPersonalizarChat(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        
        layout = BoxLayout(orientation='vertical', spacing=0)
        header = BoxLayout(size_hint=(1, None), height=55, padding=[10, 0, 16, 0], spacing=10)
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self.rect_header = RoundedRectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, s: setattr(self.rect_header, 'size', s), pos=lambda i, s: setattr(self.rect_header, 'pos', s))

        btn_volver = BotonVolverVectorial()
        btn_volver.bind(on_release=lambda x: setattr(self.manager, 'current', 'pantalla_ajustes'))
        lbl_titulo = Label(text="Personalizar Chat", font_size='18sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle')
        lbl_titulo.bind(size=lbl_titulo.setter('text_size'))

        btn_guardar = Button(text="Guardar", size_hint=(None, None), size=(80, 40), pos_hint={'center_y': 0.5}, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_guardar.bind(on_release=self.guardar_y_volver)

        header.add_widget(btn_volver)
        header.add_widget(lbl_titulo)
        header.add_widget(btn_guardar)
        layout.add_widget(header)

        scroll_cuerpo = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True)
        columnas_layout = BoxLayout(orientation='vertical', spacing=20, size_hint_y=None, padding=[15, 20, 15, 20])
        columnas_layout.bind(minimum_height=columnas_layout.setter('height'))

        scroll_horizontal = ScrollView(size_hint=(1, None), height=130, do_scroll_x=True, do_scroll_y=False)
        cols_h = BoxLayout(orientation='horizontal', spacing=15, size_hint_x=None)
        cols_h.bind(minimum_width=cols_h.setter('width'))

        self.estilos_burbujas = [
            "Clásico Redondeado", "Cápsula Moderna", "Minimalista Plano", 
            "Borde Neón", "Elegante Oscuro", "Estilo Pastel Rosa", 
            "Estilo Solar Amarillo", "Azul Océano", "Estilo Retro Militar", "Magenta Vibrante"
        ]

        col1 = BoxLayout(orientation='vertical', spacing=8, size_hint_x=None, width=110)
        l1 = Label(text="Tamaño\nDe fuente", font_size='13sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=45, halign='center')
        l1.bind(size=l1.setter('text_size'))
        self.spinner_fuente = Spinner(text='15', values=tuple([str(i) for i in range(4, 26)]), size_hint=(None, None), size=(110, 48), background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        col1.add_widget(l1)
        col1.add_widget(self.spinner_fuente)

        col2 = BoxLayout(orientation='vertical', spacing=8, size_hint_x=None, width=110)
        l2 = Label(text="Color\nDe fuente", font_size='13sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=45, halign='center')
        l2.bind(size=l2.setter('text_size'))
        self.colores_nombres = ["Blanco", "Negro", "Gris", "Rojo", "Verde", "Azul", "Amarillo", "Naranja", "Morado", "Rosado"]
        self.spinner_color = Spinner(text='Blanco', values=tuple(self.colores_nombres), size_hint=(None, None), size=(110, 48), background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        col2.add_widget(l2)
        col2.add_widget(self.spinner_color)

        col3 = BoxLayout(orientation='vertical', spacing=8, size_hint_x=None, width=140)
        l3 = Label(text="Tipo de\nfuente", font_size='13sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=45, halign='center')
        l3.bind(size=l3.setter('text_size'))
        self.tipos_fuente = ["Roboto", "Open Sans", "Lato", "Montserrat", "Poppins", "Inter", "Ubuntu", "Oswald", "Raleway", "Quicksand"]
        self.spinner_tipo = Spinner(text='Roboto', values=tuple(self.tipos_fuente), size_hint=(None, None), size=(140, 48), background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        col3.add_widget(l3)
        col3.add_widget(self.spinner_tipo)

        col4 = BoxLayout(orientation='vertical', spacing=8, size_hint_x=None, width=160)
        l4 = Label(text="Estilo burbujas\nde IA", font_size='13sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=45, halign='center')
        l4.bind(size=l4.setter('text_size'))
        self.spinner_burbuja_ia = Spinner(text='Clásico Redondeado', values=tuple(self.estilos_burbujas), size_hint=(None, None), size=(160, 48), background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        col4.add_widget(l4)
        col4.add_widget(self.spinner_burbuja_ia)

        col5 = BoxLayout(orientation='vertical', spacing=8, size_hint_x=None, width=160)
        l5 = Label(text="Estilo burbujas\nde usuario", font_size='13sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=45, halign='center')
        l5.bind(size=l5.setter('text_size'))
        self.spinner_burbuja_usuario = Spinner(text='Clásico Redondeado', values=tuple(self.estilos_burbujas), size_hint=(None, None), size=(160, 48), background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        col5.add_widget(l5)
        col5.add_widget(self.spinner_burbuja_usuario)

        cols_h.add_widget(col1)
        cols_h.add_widget(col2)
        cols_h.add_widget(col3)
        cols_h.add_widget(col4)
        cols_h.add_widget(col5)
        scroll_horizontal.add_widget(cols_h)
        columnas_layout.add_widget(scroll_horizontal)

        box_img_fondo = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None, height=90)
        lbl_img_fondo = Label(text="Imagen de fondo", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), halign='left', size_hint_y=None, height=25)
        lbl_img_fondo.bind(size=lbl_img_fondo.setter('text_size'))
        self.btn_subir_fondo = Button(text="Seleccionar foto de fondo...", size_hint_y=None, height=48, background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        self.btn_subir_fondo.bind(on_release=self.seleccionar_imagen_fondo)
        box_img_fondo.add_widget(lbl_img_fondo)
        box_img_fondo.add_widget(self.btn_subir_fondo)
        columnas_layout.add_widget(box_img_fondo)

        box_fondo_solido = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None, height=90)
        lbl_fondo_solido = Label(text="Fondo sólido", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), halign='left', size_hint_y=None, height=25)
        lbl_fondo_solido.bind(size=lbl_fondo_solido.setter('text_size'))
        
        self.spinner_fondo_solido = Spinner(text="Negro Carbón", values=tuple(app.MAPA_COLORES_SOLIDOS.keys()), size_hint_y=None, height=48, background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        box_fondo_solido.add_widget(lbl_fondo_solido)
        box_fondo_solido.add_widget(self.spinner_fondo_solido)
        columnas_layout.add_widget(box_fondo_solido)

        box_color_ambiente = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None, height=90)
        lbl_color_ambiente = Label(text="Color de ambiente", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), halign='left', size_hint_y=None, height=25)
        lbl_color_ambiente.bind(size=lbl_color_ambiente.setter('text_size'))
        
        self.spinner_color_ambiente = Spinner(text="Azul Oscuro Clásico", values=tuple(app.MAPA_COLORES_AMBIENTE.keys()), size_hint_y=None, height=48, background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        box_color_ambiente.add_widget(lbl_color_ambiente)
        box_color_ambiente.add_widget(self.spinner_color_ambiente)
        columnas_layout.add_widget(box_color_ambiente)

        scroll_cuerpo.add_widget(columnas_layout)
        layout.add_widget(scroll_cuerpo)
        self.add_widget(layout)

    def seleccionar_imagen_fondo(self, instance):
        if filechooser:
            filechooser.open_file(on_selection=self.imagen_fondo_seleccionada, filters=[("Imágenes", "*.png", "*.jpg", "*.jpeg")])
        else:
            print("Filechooser no disponible.")

    def imagen_fondo_seleccionada(self, seleccion):
        if seleccion:
            app = App.get_running_app()
            app.chat_imagen_fondo = seleccion[0]
            self.btn_subir_fondo.text = f"Fondo: {os.path.basename(seleccion[0])}"

    def on_pre_enter(self):
        app = App.get_running_app()
        self.spinner_fuente.text = str(app.tamano_fuente)
        self.spinner_color.text = app.color_fuente
        self.spinner_tipo.text = app.tipo_fuente_estilo
        self.spinner_burbuja_ia.text = app.estilo_burbuja_ia
        self.spinner_burbuja_usuario.text = app.estilo_burbuja_usuario
        self.spinner_fondo_solido.text = app.chat_fondo_solido
        self.spinner_color_ambiente.text = app.chat_color_ambiente
        if app.chat_imagen_fondo:
            self.btn_subir_fondo.text = f"Fondo: {os.path.basename(app.chat_imagen_fondo)}"
        else:
            self.btn_subir_fondo.text = "Seleccionar foto de fondo..."

    def guardar_y_volver(self, instance):
        app = App.get_running_app()
        try:
            app.tamano_fuente = int(self.spinner_fuente.text)
        except ValueError:
            app.tamano_fuente = 15
        app.color_fuente = self.spinner_color.text
        app.tipo_fuente_estilo = self.spinner_tipo.text
        app.estilo_burbuja_ia = self.spinner_burbuja_ia.text
        app.estilo_burbuja_usuario = self.spinner_burbuja_usuario.text
        app.chat_fondo_solido = self.spinner_fondo_solido.text
        app.chat_color_ambiente = self.spinner_color_ambiente.text
        app.guardar_datos()
        self.manager.current = 'pantalla_ajustes'

class PantallaInformacionUsuario(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=0)
        header = BoxLayout(size_hint=(1, None), height=55, padding=[10, 0, 16, 0], spacing=10)
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self.rect_header = RoundedRectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, s: setattr(self.rect_header, 'size', s), pos=lambda i, s: setattr(self.rect_header, 'pos', s))

        btn_volver = BotonVolverVectorial()
        btn_volver.bind(on_release=lambda x: setattr(self.manager, 'current', 'pantalla_ajustes'))
        lbl_titulo = Label(text="Información de usuario", font_size='18sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle')
        lbl_titulo.bind(size=lbl_titulo.setter('text_size'))

        btn_guardar = Button(text="Guardar", size_hint=(None, None), size=(80, 40), pos_hint={'center_y': 0.5}, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_guardar.bind(on_release=self.guardar_y_volver)

        header.add_widget(btn_volver)
        header.add_widget(lbl_titulo)
        header.add_widget(btn_guardar)
        layout.add_widget(header)

        scroll_cuerpo = ScrollView(size_hint=(1, 1))
        cuerpo = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None, padding=[20, 20, 20, 20])
        cuerpo.bind(minimum_height=cuerpo.setter('height'))

        self.btn_elegir_img_usuario = Button(text="Seleccionar imagen de perfil...", size_hint_y=None, height=48, background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        self.btn_elegir_img_usuario.bind(on_release=lambda x: filechooser.open_file(on_selection=self.imagen_usuario_seleccionada, filters=[("Imágenes", "*.png", "*.jpg", "*.jpeg")]) if filechooser else None)

        self.input_nombre = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='15sp', hint_text="Tu nombre...")
        self.input_apodo = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='15sp', hint_text="Tu apodo...")
        self.input_edad = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='15sp', hint_text="Edad...")
        self.input_altura = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='15sp', hint_text="Altura...")
        self.input_descripcion = TextInput(text="", multiline=True, size_hint_y=None, height=140, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 12, 12, 12], font_size='14sp', hint_text="Descripción...")

        for w in [Label(text="Imagen de perfil", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.btn_elegir_img_usuario,
                  Label(text="Nombre", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_nombre,
                  Label(text="Apodo", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_apodo,
                  Label(text="Edad", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_edad,
                  Label(text="Altura", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_altura,
                  Label(text="Descripción", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_descripcion]:
            cuerpo.add_widget(w)

        cuerpo.add_widget(Widget())
        scroll_cuerpo.add_widget(cuerpo)
        layout.add_widget(scroll_cuerpo)
        self.add_widget(layout)

    def imagen_usuario_seleccionada(self, seleccion):
        if seleccion:
            app = App.get_running_app()
            app.imagen_usuario = seleccion[0]
            self.btn_elegir_img_usuario.text = f"Perfil: {os.path.basename(seleccion[0])}"

    def on_pre_enter(self):
        app = App.get_running_app()
        self.input_nombre.text = app.info_usuario.get("nombre", "")
        self.input_apodo.text = app.info_usuario.get("apodo", "")
        self.input_edad.text = app.info_usuario.get("edad", "")
        self.input_altura.text = app.info_usuario.get("altura", "")
        self.input_descripcion.text = app.info_usuario.get("descripcion", "")
        if app.imagen_usuario:
            self.btn_elegir_img_usuario.text = f"Perfil: {os.path.basename(app.imagen_usuario)}"
        else:
            self.btn_elegir_img_usuario.text = "Seleccionar imagen de perfil..."

    def guardar_y_volver(self, instance):
        app = App.get_running_app()
        app.info_usuario = {
            "nombre": self.input_nombre.text.strip(),
            "apodo": self.input_apodo.text.strip(),
            "edad": self.input_edad.text.strip(),
            "altura": self.input_altura.text.strip(),
            "descripcion": self.input_descripcion.text.strip()
        }
        app.guardar_datos()
        self.manager.current = 'pantalla_ajustes'

class PantallaPersonalizacion(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=0)
        header = BoxLayout(size_hint=(1, None), height=55, padding=[10, 0, 16, 0], spacing=10)
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self.rect_header = RoundedRectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda i, s: setattr(self.rect_header, 'size', s), pos=lambda i, s: setattr(self.rect_header, 'pos', s))

        btn_volver = BotonVolverVectorial()
        btn_volver.bind(on_release=lambda x: setattr(self.manager, 'current', 'pantalla_ajustes'))
        lbl_titulo = Label(text="Personalización", font_size='18sp', bold=True, color=(1, 1, 1, 1), halign='left', valign='middle')
        lbl_titulo.bind(size=lbl_titulo.setter('text_size'))

        btn_guardar = Button(text="Guardar", size_hint=(None, None), size=(80, 40), pos_hint={'center_y': 0.5}, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_guardar.bind(on_release=self.guardar_y_volver)

        header.add_widget(btn_volver)
        header.add_widget(lbl_titulo)
        header.add_widget(btn_guardar)
        layout.add_widget(header)

        scroll_cuerpo = ScrollView(size_hint=(1, 1))
        cuerpo = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None, padding=[20, 20, 20, 20])
        cuerpo.bind(minimum_height=cuerpo.setter('height'))

        self.btn_elegir_imagen = Button(text="Seleccionar archivo de imagen...", size_hint_y=None, height=48, background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        self.btn_elegir_imagen.bind(on_release=lambda x: filechooser.open_file(on_selection=self.imagen_ia_seleccionada, filters=[("Imágenes", "*.png", "*.jpg", "*.jpeg")]) if filechooser else None)

        self.input_nombre_ia = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='15sp')
        
        layout_pers_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=100)
        self.input_personalidad = TextInput(text="", multiline=True, size_hint_x=0.78, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 12, 12, 12], font_size='14sp')
        btn_pegar_pers = Button(text="Pegar", size_hint_x=0.22, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_pegar_pers.bind(on_release=lambda x: setattr(self.input_personalidad, 'text', (Clipboard.paste() or "").strip()))
        layout_pers_box.add_widget(self.input_personalidad)
        layout_pers_box.add_widget(btn_pegar_pers)

        layout_voz_opciones = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, spacing=10)
        self.btn_voz_mujer = Button(text="✔ Voz Mujer", background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        self.btn_voz_hombre = Button(text="Voz Hombre", background_color=(0.3, 0.3, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        self.btn_voz_mujer.bind(on_release=lambda x: self.seleccionar_genero_voz("mujer"))
        self.btn_voz_hombre.bind(on_release=lambda x: self.seleccionar_genero_voz("hombre"))
        layout_voz_opciones.add_widget(self.btn_voz_mujer)
        layout_voz_opciones.add_widget(self.btn_voz_hombre)

        btn_probar_voz = Button(text="🔊 Probar Voces", size_hint_y=None, height=46, background_color=(0.15, 0.5, 0.8, 1), color=(1, 1, 1, 1), bold=True)
        btn_probar_voz.bind(on_release=lambda x: GestorVoz.hablar(f"Hola, soy {self.input_nombre_ia.text or 'Kamila'}.", App.get_running_app().tipo_voz))

        layout_apikey_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=54)
        self.input_apikey = TextInput(text="", multiline=False, size_hint_x=0.78, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='13sp')
        btn_pegar_api = Button(text="Pegar", size_hint_x=0.22, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_pegar_api.bind(on_release=lambda x: setattr(self.input_apikey, 'text', (Clipboard.paste() or "").replace("\n", "").strip()))
        layout_apikey_box.add_widget(self.input_apikey)
        layout_apikey_box.add_widget(btn_pegar_api)

        layout_switch = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, spacing=10)
        self.switch_apikey = Switch(active=False, size_hint_x=None, width=80)
        layout_switch.add_widget(Label(text="Conectar apikey", font_size='15sp', bold=True, color=(1, 1, 1, 1), halign='left'))
        layout_switch.add_widget(self.switch_apikey)

        self.input_titulo_aprendizaje = TextInput(text="", multiline=False, size_hint_y=None, height=48, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 14, 12, 10], font_size='14sp', hint_text="Título...")
        self.input_inyeccion = TextInput(text="", multiline=True, size_hint_y=None, height=140, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), cursor_color=(1, 1, 1, 1), padding=[12, 12, 12, 12], font_size='13sp', hint_text="Pregunta=Respuesta")
        
        btn_guardar_aprend = Button(text="Guardar aprendizaje", size_hint_y=None, height=46, background_color=(0.1, 0.7, 0.3, 1), color=(1, 1, 1, 1), bold=True)
        btn_guardar_aprend.bind(on_release=self.ejecutar_guardar_aprendizaje)

        for w in [Label(text="Imagen de IA", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.btn_elegir_imagen,
                  Label(text="Nombre de IA", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_nombre_ia,
                  Label(text="Personalidad", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), layout_pers_box,
                  Label(text="Voces", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), layout_voz_opciones, btn_probar_voz,
                  Label(text="API Key", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), layout_apikey_box, layout_switch,
                  Label(text="Título de aprendizaje", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_titulo_aprendizaje,
                  Label(text="Inyección masiva", font_size='15sp', bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_y=None, height=24), self.input_inyeccion, btn_guardar_aprend]:
            cuerpo.add_widget(w)

        cuerpo.add_widget(Widget())
        scroll_cuerpo.add_widget(cuerpo)
        layout.add_widget(scroll_cuerpo)
        self.add_widget(layout)

    def imagen_ia_seleccionada(self, seleccion):
        if seleccion:
            app = App.get_running_app()
            app.imagen_ia = seleccion[0]
            self.btn_elegir_imagen.text = f"Imagen IA: {os.path.basename(seleccion[0])}"

    def seleccionar_genero_voz(self, genero):
        App.get_running_app().tipo_voz = genero
        if genero == "mujer":
            self.btn_voz_mujer.text = "✔ Voz Mujer"
            self.btn_voz_mujer.background_color = (0.1, 0.7, 0.3, 1)
            self.btn_voz_hombre.text = "Voz Hombre"
            self.btn_voz_hombre.background_color = (0.3, 0.3, 0.3, 1)
        else:
            self.btn_voz_hombre.text = "✔ Voz Hombre"
            self.btn_voz_hombre.background_color = (0.1, 0.7, 0.3, 1)
            self.btn_voz_mujer.text = "Voz Mujer"
            self.btn_voz_mujer.background_color = (0.3, 0.3, 0.3, 1)

    def on_pre_enter(self):
        app = App.get_running_app()
        self.input_nombre_ia.text = app.nombre_ia
        self.input_personalidad.text = app.personalidad_ia
        self.seleccionar_genero_voz(app.tipo_voz)
        self.input_apikey.text = app.apikey_ia
        self.switch_apikey.active = app.usar_apikey
        if app.imagen_ia:
            self.btn_elegir_imagen.text = f"Imagen IA: {os.path.basename(app.imagen_ia)}"
        else:
            self.btn_elegir_imagen.text = "Seleccionar archivo de imagen..."

    def ejecutar_guardar_aprendizaje(self, instance):
        app = App.get_running_app()
        bloque = self.input_inyeccion.text.strip()
        titulo = self.input_titulo_aprendizaje.text.strip()
        if bloque and titulo:
            app.conocimientos_aprendidos.append({"titulo": titulo, "bloque": bloque})
            app.guardar_datos()
            self.input_inyeccion.text = ""
            self.input_titulo_aprendizaje.text = ""
            self.manager.current = 'pantalla_chat'

    def guardar_y_volver(self, instance):
        app = App.get_running_app()
        if nuevo_nombre := self.input_nombre_ia.text.strip():
            app.nombre_ia = nuevo_nombre
        app.personalidad_ia = self.input_personalidad.text.strip()
        app.apikey_ia = self.input_apikey.text.strip().replace("\n", "").replace("\r", "")
        app.usar_apikey = self.switch_apikey.active
        app.guardar_datos()
        self.manager.current = 'pantalla_ajustes'

class KamilaApp(App):
    nombre_ia = "KAMILA"
    personalidad_ia = "Amable, empática, conversacional y motivadora"
    tipo_voz = "mujer"
    imagen_ia = ""
    imagen_usuario = ""
    apikey_ia = ""
    usar_apikey = False
    tamano_fuente = 15
    color_fuente = "Blanco"
    tipo_fuente_estilo = "Roboto"
    estilo_burbuja_ia = "Clásico Redondeado"
    estilo_burbuja_usuario = "Clásico Redondeado"
    chat_imagen_fondo = ""
    chat_fondo_solido = "Negro Carbón"
    chat_color_ambiente = "Azul Oscuro Clásico"
    conocimientos_aprendidos = []
    info_usuario = {"nombre": "", "apodo": "", "edad": "", "altura": "", "descripcion": ""}
    ARCHIVO_DATOS = "kamila_datos.json"

    MAPA_COLORES_SOLIDOS = {
        "Negro Profundo": "#111111",
        "Negro Carbón": "#1a1a2e",
        "Azul Noche Profundo": "#0f3460",
        "Azul Marino Oscuro": "#16213e",
        "Gris Antracita": "#222831",
        "Verde Esmeralda Dual": "#1f4037",
        "Azul Océano Dual": "#2c3e50",
        "Gris Acero Dual": "#373b44",
        "Gris Oscuro Dual": "#232526",
        "Índigo Neón Dual": "#4e54c8",
        "Azul Espacial Dual": "#141e30",
        "Azul Petróleo Dual": "#2b5876",
        "Gris Pizarra Dual": "#3a6073",
        "Violeta Nocturno Dual": "#1f1c2c",
        "Azul Metálico Dual": "#283048"
    }

    MAPA_COLORES_AMBIENTE = {
        "Azul Oscuro Clásico": "#2C3E50",
        "Azul Pizarra Oscuro": "#34495E",
        "Morado Profundo": "#4A235A",
        "Púrpura Misterioso": "#512E5F",
        "Azul Océano Profundo": "#1B4F72",
        "Azul Acero Medio": "#21618C",
        "Verde Bosque Oscuro": "#0E6251",
        "Verde Petróleo Sutil": "#117A65",
        "Oliva Profundo": "#7D6608",
        "Marrón Dorado Oscuro": "#7E5109",
        "Rojo Ladrillo Oscuro": "#78281F",
        "Rojo Vino Oscuro": "#641E16",
        "Gris Azulado Sutil": "#5D6D7E",
        "Gris Pizarra Medio": "#566573",
        "Violeta Oscuro Suave": "#4A235A",
        "Verde Bosque Vivo": "#145A32",
        "Verde Esmeralda Sutil": "#196F3D",
        "Ámbar Oscuro": "#7E5109",
        "Gris Tormenta": "#515A5A",
        "Azul Medianoche": "#273746"
    }

    def build(self):
        self.cargar_datos()
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(PantallaChat(name='pantalla_chat'))
        sm.add_widget(PantallaAjustes(name='pantalla_ajustes'))
        sm.add_widget(PantallaPersonalizacion(name='pantalla_personalizacion'))
        sm.add_widget(PantallaPersonalizarChat(name='pantalla_personalizar_chat'))
        sm.add_widget(PantallaInformacionUsuario(name='pantalla_informacion_usuario'))
        return sm

    def guardar_datos(self):
        datos = {
            "nombre_ia": self.nombre_ia, "personalidad_ia": self.personalidad_ia, "tipo_voz": self.tipo_voz,
            "imagen_ia": self.imagen_ia, "imagen_usuario": self.imagen_usuario, "apikey_ia": self.apikey_ia,
            "usar_apikey": self.usar_apikey, "tamano_fuente": self.tamano_fuente, "color_fuente": self.color_fuente,
            "tipo_fuente_estilo": self.tipo_fuente_estilo, "estilo_burbuja_ia": self.estilo_burbuja_ia,
            "estilo_burbuja_usuario": self.estilo_burbuja_usuario, "chat_imagen_fondo": self.chat_imagen_fondo,
            "chat_fondo_solido": self.chat_fondo_solido, "chat_color_ambiente": self.chat_color_ambiente,
            "conocimientos_aprendidos": self.conocimientos_aprendidos, "info_usuario": self.info_usuario
        }
        try:
            with open(self.ARCHIVO_DATOS, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar: {e}")

    def cargar_datos(self):
        if os.path.exists(self.ARCHIVO_DATOS):
            try:
                with open(self.ARCHIVO_DATOS, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    self.nombre_ia = datos.get("nombre_ia", "KAMILA")
                    self.personalidad_ia = datos.get("personalidad_ia", "Amable, empática, conversacional y motivadora")
                    self.tipo_voz = datos.get("tipo_voz", "mujer")
                    self.imagen_ia = datos.get("imagen_ia", "")
                    self.imagen_usuario = datos.get("imagen_usuario", "")
                    self.apikey_ia = datos.get("apikey_ia", "")
                    self.usar_apikey = datos.get("usar_apikey", False)
                    self.tamano_fuente = datos.get("tamano_fuente", 15)
                    self.color_fuente = datos.get("color_fuente", "Blanco")
                    self.tipo_fuente_estilo = datos.get("tipo_fuente_estilo", "Roboto")
                    self.estilo_burbuja_ia = datos.get("estilo_burbuja_ia", "Clásico Redondeado")
                    self.estilo_burbuja_usuario = datos.get("estilo_burbuja_usuario", "Clásico Redondeado")
                    self.chat_imagen_fondo = datos.get("chat_imagen_fondo", "")
                    self.chat_fondo_solido = datos.get("chat_fondo_solido", "Negro Carbón")
                    self.chat_color_ambiente = datos.get("chat_color_ambiente", "Azul Oscuro Clásico")
                    self.conocimientos_aprendidos = datos.get("conocimientos_aprendidos", [])
                    self.info_usuario = datos.get("info_usuario", self.info_usuario)
            except Exception as e:
                print(f"Error al cargar: {e}")

    def on_start(self):
        mostrar_barra_estado()

if __name__ == '__main__':
    KamilaApp().run()