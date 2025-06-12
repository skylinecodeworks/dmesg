# dmesg-ollama-tts

Monitoriza errores críticos del kernel de Linux en tiempo real y utiliza inteligencia artificial para explicarlos… ¡con síntesis de voz!

Este script:
- Observa el output de `dmesg -w` buscando patrones de error.
- Solicita a un modelo LLM local (Ollama, por defecto `qwen2.5-coder:7b`) una explicación técnica, breve y precisa.
- Genera una locución de la explicación usando [Chatterbox TTS](https://github.com/resemble-ai/chatterbox).
- Reproduce automáticamente el audio con `ffplay`.

---

## Requisitos

- **Linux** (se usa `dmesg -w` y requiere privilegios de sudo)
- **Python 3.10+**
- **ffmpeg** (para `ffplay` y manipulación de audio)
- **[Ollama](https://ollama.com/) corriendo localmente** (puerto 11434)
- **[Chatterbox TTS](https://github.com/resemble-ai/chatterbox) instalado localmente**
- **Dependencias Python**: ver abajo

### Instalación de dependencias del sistema

```bash
sudo apt-get update
sudo apt-get install ffmpeg sox
````

---

## Instalación

1. **Clona y prepara Chatterbox TTS:**

```bash
git clone https://github.com/resemble-ai/chatterbox.git
cd chatterbox
uv pip install .
```

2. **Prepara el entorno de tu aplicación y instala dependencias:**

```bash
uv pip install torchaudio requests
```

(Usa `pip` tradicional si no usas Astral uv)

3. **Asegúrate de que Ollama esté corriendo con un modelo compatible:**

```bash
ollama run qwen2.5-coder:7b
```

---

## Uso

Ejecuta el script principal como usuario con permisos para leer dmesg:

```bash
sudo uv run main.py
```

o, si usas `python` clásico:

```bash
sudo python main.py
```

---

## ¿Qué hace el script?

1. **Monitorea** el kernel (`dmesg -w`) en tiempo real.
2. **Detecta errores relevantes** usando patrones configurables (error, fail, panic, etc.).
3. **Agrupa errores** relacionados para interpretarlos juntos.
4. **Solicita a Ollama** una explicación técnica breve.
5. **Sintetiza la explicación** como audio con Chatterbox TTS.
6. **Reproduce el audio** automáticamente usando `ffplay`.

---

## Variables clave y customización

* **`ERROR_PATTERNS`**: Lista de patrones regex para identificar líneas relevantes en dmesg.
* **`MODEL`**: Nombre del modelo Ollama a usar.
* **`OLLAMA_URL`**: URL local de la API Ollama (puedes cambiar el puerto si tu instancia lo requiere).

---

## Ejemplo de flujo

1. Ocurre un error en el kernel y aparece en `dmesg`.
2. El script lo detecta y lo envía a Ollama.
3. Ollama responde con una explicación concisa.
4. Chatterbox TTS sintetiza el texto.
5. El audio resultante se reproduce automáticamente.

---

## Notas y advertencias

* El primer uso puede tardar por la descarga de modelos de Chatterbox (peso de varios GB).
* Si quieres soporte de GPU, asegúrate de instalar Chatterbox y PyTorch para CUDA.
* El audio se guarda temporalmente en `/tmp/error_dmesg_ollama.wav` y se sobrescribe con cada evento.

---

## Licencia

MIT (igual que Chatterbox)

