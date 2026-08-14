from flask import Flask, request, jsonify, make_response
from datetime import datetime
import sqlite3
import os
import json
import ipaddress
import hashlib

app = Flask(__name__)
DATA_DIR = os.environ.get('RENDER_DATA_DIR', os.path.join(os.path.dirname(__file__), 'data'))
DB_PATH = os.path.join(DATA_DIR, 'visitors.db')
BANS_PATH = os.path.join(DATA_DIR, 'bans.json')

ALLOWED_ORIGINS = ['https://bercaius.github.io', 'https://unutulmayacaklar.github.io', 'null']

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = get_db()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                user_agent TEXT,
                path TEXT,
                referrer TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS console_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                user_agent TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print('DB init error:', e)

def load_bans():
    if not os.path.exists(BANS_PATH):
        return []
    with open(BANS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_bans(bans):
    with open(BANS_PATH, 'w', encoding='utf-8') as f:
        json.dump(bans, f, ensure_ascii=False, indent=2)

def is_banned(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    bans = load_bans()
    for ban in bans:
        try:
            network = ipaddress.ip_network(ban, strict=False)
            if addr in network:
                return True
        except ValueError:
            continue
    return False

def ban_ip_cidr(cidr):
    try:
        ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False
    bans = load_bans()
    if cidr not in bans:
        bans.append(cidr)
        save_bans(bans)
    return True

def client_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    return ip

def fingerprint():
    ua = request.headers.get('User-Agent', '')
    return hashlib.sha256(f"{ua}|{request.accept_languages}|{request.accept_encodings}".encode('utf-8')).hexdigest()

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
init_db()

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


def cors_response(data, status=200):
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS:
        resp = make_response(jsonify(data), status)
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Max-Age'] = '3600'
        return resp
    return jsonify(data), status


@app.route('/api/log', methods=['POST', 'OPTIONS'])
def log_visit():
    if request.method == 'OPTIONS':
        return cors_response({})
    try:
        ip = client_ip()
        if is_banned(ip):
            return cors_response({'status': 'banned'}, 403)

        data = request.get_json(silent=True) or {}
        conn = get_db()
        conn.execute(
            'INSERT INTO visits (ip, user_agent, path, referrer, timestamp) VALUES (?, ?, ?, ?, ?)',
            (
                ip,
                data.get('userAgent', request.headers.get('User-Agent')),
                data.get('path', request.path),
                data.get('referrer', request.referrer),
                datetime.utcnow().isoformat() + 'Z'
            )
        )
        conn.commit()
        conn.close()
        return cors_response({'status': 'logged'}), 200
    except Exception as e:
        print('Log visit error:', e)
        return cors_response({'error': str(e)}), 500

@app.route('/api/console', methods=['POST', 'OPTIONS'])
def log_console():
    if request.method == 'OPTIONS':
        return cors_response({})
    try:
        ip = client_ip()
        if is_banned(ip):
            return cors_response({'status': 'banned'}, 403)

        data = request.get_json(silent=True) or {}
        conn = get_db()
        conn.execute(
            'INSERT INTO console_logs (ip, user_agent, details, timestamp) VALUES (?, ?, ?, ?)',
            (
                ip,
                data.get('userAgent', request.headers.get('User-Agent')),
                json.dumps(data.get('details', {}), ensure_ascii=False),
                datetime.utcnow().isoformat() + 'Z'
            )
        )
        conn.commit()
        conn.close()
        return cors_response({'status': 'logged'}), 200
    except Exception as e:
        print('Log console error:', e)
        return cors_response({'error': str(e)}), 500

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Max-Age'] = '3600'
    return response

@app.route('/api/banned', methods=['GET'])
def get_banned():
    bans = load_bans()
    return jsonify({'banned': bans}), 200

@app.route('/api/ban', methods=['POST'])
def ban_ip():
    data = request.get_json(silent=True) or {}
    cidr = data.get('ip') or data.get('cidr')
    if not cidr:
        return jsonify({'error': 'ip or cidr required'}), 400
    if not ban_ip_cidr(cidr):
        return jsonify({'error': 'invalid cidr'}), 400
    return jsonify({'status': 'banned', 'banned': load_bans()}), 200

@app.route('/api/unban', methods=['POST'])
def unban_ip():
    data = request.get_json(silent=True) or {}
    cidr = data.get('ip') or data.get('cidr')
    if not cidr:
        return jsonify({'error': 'ip or cidr required'}), 400
    bans = load_bans()
    if cidr in bans:
        bans = [b for b in bans if b != cidr]
        save_bans(bans)
    return jsonify({'status': 'unbanned', 'banned': bans}), 200

@app.route('/api/check-ban', methods=['GET'])
def check_ban():
    ip = client_ip()
    banned = is_banned(ip)
    return jsonify({'ip': ip, 'banned': banned}), 200

@app.route('/api/visitors', methods=['GET'])
def visitors():
    conn = get_db()
    rows = conn.execute('SELECT * FROM visits ORDER BY id DESC LIMIT 200').fetchall()
    conn.close()
    return jsonify({'visitors': [dict(r) for r in rows]}), 200

@app.route('/api/console-logs', methods=['GET'])
def console_logs():
    conn = get_db()
    rows = conn.execute('SELECT * FROM console_logs ORDER BY id DESC LIMIT 200').fetchall()
    conn.close()
    return jsonify({'logs': [dict(r) for r in rows]}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
