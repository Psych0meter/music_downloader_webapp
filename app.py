import os
import json
import logging
import sys
import importlib.util
import inspect
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from providers.base import BaseProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- DYNAMIC PLUGIN LOADER ---
PROVIDERS = {}

def load_providers():
    providers_dir = os.path.join(os.path.dirname(__file__), 'providers')
    for filename in os.listdir(providers_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
            module_name = filename[:-3]
            filepath = os.path.join(providers_dir, filename)
            
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseProvider) and obj is not BaseProvider:
                    inst = obj()
                    PROVIDERS[inst.id] = inst
                    logger.info(f"Loaded provider: {inst.name} ({inst.id})")

load_providers()

# --- ROUTES ---
@app.route('/')
def index():
    # Pass the list of loaded providers to the frontend
    return render_template('index.html', providers=list(PROVIDERS.values()))

@app.route('/api/info/<provider_id>')
def provider_info(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Provider not found"}), 404
    return jsonify(PROVIDERS[provider_id].get_info())

@app.route('/api/search/<provider_id>', methods=['POST'])
def search(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Provider not found"}), 404
    try:
        return jsonify({"results": PROVIDERS[provider_id].search(request.json.get('query', ''))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<provider_id>', methods=['POST'])
def download(provider_id):
    if provider_id not in PROVIDERS: return jsonify({"error": "Provider not found"}), 404

    def generate():
        try:
            for log_data in PROVIDERS[provider_id].download(request.json):
                yield f"data: {json.dumps(log_data)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'line': f'<span class=\"text-red-400\">System Error: {str(e)}</span>', 'progress': 100})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)