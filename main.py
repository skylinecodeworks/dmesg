import subprocess
import re
import time
import requests
import threading
import queue

import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b"

ERROR_PATTERNS = [
    r'error',
    r'fail',
    r'segfault',
    r'corrupt',
    r'panic',
    r'critical'
]

tts = ChatterboxTTS.from_pretrained(device="cpu")


def line_has_error(line):
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in ERROR_PATTERNS)

def interpretar_error_ollama(error_msg):
    prompt = (
        f"Te paso este mensaje de error del kernel de Linux:\n"
        f"{error_msg}\n"
        f"¿Podrías explicarme en una sola frase, tecnicamente, qué significa? Utilza un máximo de diez palabras, sin utilizar expresiones coloquiales, eres un experto técnico. Cuando el error sea demasiado genérico simplemente menciona el origen del error."
    )
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"[No se pudo obtener interpretación de Ollama: {e}]"


def productor(q, stop_event):
    print("Abriendo dmesg -w...")
    process = subprocess.Popen(['sudo', 'dmesg', '-w'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while not stop_event.is_set():
            line = process.stdout.readline()
            if not line:
                break
            # print(f"[DMESG] {line.strip()}")  # Mostrar absolutamente todo
            if line_has_error(line):
                q.put(line.strip())
    except Exception as e:
        print(f"Error en el productor: {e}")
    finally:
        process.terminate()


def consumidor(q, stop_event, group_window=2):
    error_buffer = []
    last_time = None

    while not stop_event.is_set():
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            # Si hay errores en el buffer y pasó suficiente tiempo, procesamos el grupo
            if error_buffer and (time.time() - last_time > group_window):
                enviar_grupo_a_ollama(error_buffer)
                error_buffer.clear()
            continue
        if msg is None:
            # Antes de salir, procesa lo que haya en el buffer
            if error_buffer:
                enviar_grupo_a_ollama(error_buffer)
            break
        # print(f"\n[ERROR DETECTADO] {msg}")
        error_buffer.append(msg)
        last_time = time.time()
        # Si el buffer llega a cierto tamaño, lo enviamos igual para no esperar eternamente
        if len(error_buffer) >= 10:
            enviar_grupo_a_ollama(error_buffer)
            error_buffer.clear()

def enviar_grupo_a_ollama(errores):
    if len(errores) == 1:
        interpretacion = interpretar_error_ollama(errores[0])
        print(f"[INTERPRETACIÓN OLLAMA]\n{interpretacion}\n")
        wav = tts.generate(interpretacion)
        ta.save("/tmp/error_dmesg_ollama.wav", wav, tts.sr)
        subprocess.Popen(["ffplay", "-autoexit", "-nodisp", "/tmp/error_dmesg_ollama.wav"])
    else:
        mensajes = "\n".join(errores)
        prompt = (
            f"Han ocurrido estos mensajes de error del kernel de Linux seguidos:\n"
            f"{mensajes}\n"
            f"¿Podrías explicarme en una sola frase, tecnicamente, qué significa? Utilza un máximo de diez palabras, sin utilizar expresiones coloquiales, eres un experto técnico. Cuando el error sea demasiado genérico simplemente menciona el origen del error."
        )
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            print(f"[INTERPRETACIÓN OLLAMA]\n{data.get('response', '').strip()}\n")
            interpretacion = data.get('response', '').strip()
            wav = tts.generate(interpretacion)
            ta.save("/tmp/error_dmesg_ollama.wav", wav, tts.sr)
            subprocess.Popen(["ffplay", "-autoexit", "-nodisp", "/tmp/error_dmesg_ollama.wav"])

        except Exception as e:
            print(f"[No se pudo obtener interpretación de Ollama: {e}]")

def main():
    q = queue.Queue()
    stop_event = threading.Event()
    prod_thread = threading.Thread(target=productor, args=(q, stop_event))
    cons_thread = threading.Thread(target=consumidor, args=(q, stop_event))

    prod_thread.start()
    cons_thread.start()

    try:
        prod_thread.join()
        cons_thread.join()
    except KeyboardInterrupt:
        print("\nFinalizando monitoreo.")
        stop_event.set()
        q.put(None)
        prod_thread.join()
        cons_thread.join()

if __name__ == "__main__":
    main()
