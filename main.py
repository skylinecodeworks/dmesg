import subprocess
import re
import requests
import threading
import queue

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

def line_has_error(line):
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in ERROR_PATTERNS)

def interpretar_error_ollama(error_msg):
    prompt = (
        f"El siguiente mensaje de error fue registrado por el kernel de Linux:\n"
        f"{error_msg}\n"
        f"Explica en castellano simple qué significa este error, qué lo puede causar y cómo podría solucionarse."
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

def productor(q):
    process = subprocess.Popen(['dmesg', '-w'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for line in process.stdout:
            if line_has_error(line):
                q.put(line.strip())
    except Exception as e:
        print(f"Error en el productor: {e}")
    finally:
        process.terminate()

def consumidor(q):
    while True:
        msg = q.get()
        if msg is None:
            break
        print(f"\n[ERROR DETECTADO] {msg}")
        interpretacion = interpretar_error_ollama(msg)
        print(f"[INTERPRETACIÓN OLLAMA]\n{interpretacion}\n")
        q.task_done()

def main():
    q = queue.Queue()
    prod_thread = threading.Thread(target=productor, args=(q,), daemon=True)
    cons_thread = threading.Thread(target=consumidor, args=(q,), daemon=True)

    prod_thread.start()
    cons_thread.start()

    try:
        while True:
            pass  # Espera infinita, puedes agregar otras lógicas aquí
    except KeyboardInterrupt:
        print("\nFinalizando monitoreo.")
        q.put(None)  # Señal para terminar el consumidor
        cons_thread.join(timeout=2)

if __name__ == "__main__":
    main()

