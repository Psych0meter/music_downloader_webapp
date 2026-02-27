import os
import json
import logging
import sys
import importlib.util
import inspect
from collections import deque
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from providers.base import BaseProvider

# Custom handler to store logs for the web view
class WebLogHandler(logging.Handler):
    def __init__(self, capacity=200):
        super().__init__()
        self.buffer = deque(maxlen=capacity)
    def emit(self, record):
        self.buffer.append(self.format(record))

log_handler = WebLogHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout), log_handler])
logger = logging.getLogger("MediaVault")

app = Flask(__name__)
PROVIDERS = {}

def load_providers():
    providers_dir = os.path.join(os.path.dirname(__file__), 'providers')
    if not os.path.exists(providers_dir): os.makedirs(providers_dir)
    for filename in os.listdir(providers_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(providers_dir, filename))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseProvider) and obj is not BaseProvider:
                    PROVIDERS[obj.id] = obj()
                    logger.info(f"Plugin Loaded: {obj.id}")

load_providers()

@app.route('/')
def index():
    return render_template('index.html', providers=list(PROVIDERS.values()))

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

@app.route('/api/system/logs')
def get_system_logs():
    return jsonify({"logs": list(log_handler.buffer)})

@app.route('/api/info/<provider_id>')
def provider_info(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Not found"}), 404
    return jsonify(PROVIDERS[provider_id].get_info())

@app.route('/api/search/<provider_id>', methods=['POST'])
def search(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Not found"}), 404
    return jsonify({"results": PROVIDERS[provider_id].search(request.json.get('query', ''))})

@app.route('/api/download/<provider_id>', methods=['POST'])
def download(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Not found"}), 404
    def generate():
        try:
            for log_data in PROVIDERS[provider_id].download(request.json):
                yield f"data: {json.dumps(log_data)}\n\n"
        except Exception as e:
            logger.error(f"Download Task Failed: {str(e)}")
            yield f"data: {json.dumps({'line': f'Critical Error: {str(e)}', 'progress': 100})}\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)