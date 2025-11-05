from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from buff_auto_notification.registration import register_api, login_api

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    result = register_api(phone, password)
    return jsonify(result)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    result = login_api(phone, password)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)