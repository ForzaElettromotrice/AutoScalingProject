from flask import Flask

app = Flask(__name__)

import time
from multiprocessing import Process

def cpu_load():
    busy_time = 0.3
    idle_time = 0.7
    for i in range(300):
        start_time = time.time()
        while (time.time() - start_time) < busy_time:
            pass
        time.sleep(idle_time)
    return

@app.route('/')
def home():
    return "Ok"

@app.route('/test')
def test():
    p = Process(target=cpu_load)
    p.start()
    return f"Sono una pagina!!!\n"

if __name__ == 'main':
    app.run(host='0.0.0.0', port=5000)