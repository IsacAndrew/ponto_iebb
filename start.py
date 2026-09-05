import os, socket, threading, time, webbrowser
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
load_dotenv(ROOT/'.env')
port=5050
while port<=5099:
    with socket.socket() as sock:
        try: sock.bind(('127.0.0.1',port)); break
        except OSError: port+=1
if port>5099: raise SystemExit('Nenhuma porta disponível entre 5050 e 5099.')
def open_browser():
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1)
            webbrowser.open(f'http://127.0.0.1:{port}')
            return
        except Exception: time.sleep(.5)
threading.Thread(target=open_browser,daemon=True).start()
print(f'Livro-Ponto: http://127.0.0.1:{port}\nPara encerrar, feche esta janela.')
uvicorn.run('backend.main:app',host='127.0.0.1',port=port)
