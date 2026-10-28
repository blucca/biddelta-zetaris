"""Loopback-only replay bench; Zetaris executes every evidence query."""
import argparse
import base64
import csv
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from domain import DATA, apply_plan, fixture, plan_from_native

APP = Path(__file__).parent
LOCK = threading.RLock()


def utc():
    return datetime.now(timezone.utc).isoformat()


def session_due(session):
    """Vendor JWTs last 15 minutes; expired tokens produce HTTP 400 on this bundle."""
    token = session.get('idToken') or session.get('token') or session.get('accessToken') or ''
    try:
        payload = token.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        return claims['exp'] <= time.time() + 30
    except (IndexError, ValueError, KeyError):
        return False


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.replace(pending, path)


def serve(args):
    feed = args.workspace / 'temp/zetaris-native/http/tasks_current.json'
    runtime = args.workspace / 'temp/biddelta-runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    session_path = args.workspace / '.private/zetaris/api-session-20261028.json'
    sql = (APP / 'federation.sql').read_text()
    plans = {p.stem.removeprefix('plan-'): json.loads(p.read_text()) for p in runtime.glob('plan-*.json')}

    def read_source():
        return json.loads(feed.read_text())

    def login():
        env_path = args.workspace / 'products/zetaris/zetaris-platform/.env'
        if not env_path.exists():
            env_path = args.workspace / '.private/zetaris/bundle-20261028/zetaris-platform/.env'
        env = dict(line.split('=', 1) for line in env_path.read_text().splitlines()
                   if '=' in line and not line.startswith('#'))
        req = Request(args.zetaris_url + '/api/auth/login', method='POST',
                      headers={'Content-Type': 'application/json'},
                      data=json.dumps({'username': env['ZETARIS_ADMIN_EMAIL'],
                                       'password': env['ZETARIS_ADMIN_PASSWORD']}).encode())
        with urlopen(req, timeout=30) as response:
            session = json.load(response)
        assert isinstance(session.get('orgId'), int), 'Zetaris login returned no organization'
        atomic_json(session_path, session)
        session_path.chmod(0o600)
        return session

    def native_query():
        session = json.loads(session_path.read_text()) if session_path.exists() else login()
        if session_due(session):
            session = login()
        request_id = str(uuid.uuid4())
        path = '/api/proxy/query/sql/start'
        started = time.monotonic()
        for attempt in range(2):
            token = session.get('idToken') or session.get('token') or session.get('accessToken')
            req = Request(args.zetaris_url + path, method='POST',
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token,
                                   'X-Org-ID': str(session['orgId']), 'X-Request-ID': request_id},
                          data=json.dumps({'select': sql, 'pageLimit': 100}).encode())
            try:
                with urlopen(req, timeout=90) as response:
                    raw = json.load(response)
                break
            except HTTPError as error:
                if error.code == 401 and attempt == 0:
                    session = login()
                    continue
                failure = {'utc': utc(), 'request_id': request_id, 'route': path, 'sql': sql,
                           'http_status': error.code, 'error_body': error.read().decode(errors='replace')}
                atomic_json(runtime / ('query-failed-' + request_id + '.json'), failure)
                raise
        record = {'utc': utc(), 'request_id': request_id, 'route': path, 'http_status': 200,
                  'duration_ms': round((time.monotonic() - started) * 1000), 'sql': sql, 'response': raw}
        atomic_json(runtime / ('query-' + request_id + '.json'), record)
        plan = plan_from_native(raw)
        plan.update(plan_id=request_id, queried_at=record['utc'])
        plans[request_id] = plan
        atomic_json(runtime / ('plan-' + request_id + '.json'), plan)
        return {'plan': plan, 'native': record, 'source': read_source()}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *hargs, **kwargs):
            super().__init__(*hargs, directory=str(APP / 'web'), **kwargs)

        def json_response(self, value, status=200):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/api/state':
                with LOCK:
                    return self.json_response({'source': read_source(), 'sql': sql,
                                               'documents': list(csv.DictReader((DATA / 'document_register.csv').open())),
                                               'platform': 'Zetaris vendor platform / native Spark query'})
            return super().do_GET()

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size > 8192:
                    return self.json_response({'error': 'Request exceeds replay action size'}, 413)
                body = json.loads(self.rfile.read(size) or b'{}')
                with LOCK:
                    if self.path == '/api/query':
                        return self.json_response(native_query())
                    if self.path == '/api/demo/reset':
                        initial = fixture('tasks_initial')
                        atomic_json(feed, initial)
                        event = {'utc': utc(), 'event': 'reset_historical_sample', 'snapshot_version': 1}
                        atomic_json(runtime / ('reset-' + str(uuid.uuid4()) + '.json'), event)
                        return self.json_response({'source': initial, 'event': event})
                    if self.path == '/api/demo/teammate-edit':
                        current = read_source()
                        if {t['snapshot_version'] for t in current['rows']} != {1}:
                            return self.json_response({'error': 'Reset the sample before adding its teammate edit'}, 409)
                        edited = fixture('tasks_user_edit')
                        atomic_json(feed, edited)
                        event = {'utc': utc(), 'event': 'illustrative_teammate_edit', 'task_id': 'T2',
                                 'task_version': 2, 'snapshot_version': 2,
                                 'note': next(t['notes'] for t in edited['rows'] if t['task_id'] == 'T2')}
                        atomic_json(runtime / ('edit-' + str(uuid.uuid4()) + '.json'), event)
                        return self.json_response({'source': edited, 'event': event})
                    if self.path == '/api/apply':
                        plan_id = body.get('plan_id')
                        if plan_id not in plans:
                            return self.json_response({'error': 'Run a fresh Zetaris source query to create a plan'}, 404)
                        current = read_source()
                        next_data, result = apply_plan(current, plans[plan_id])
                        result.update(utc=utc(), plan_id=plan_id)
                        if result['result'] == 'applied' and result['writes']:
                            atomic_json(feed, next_data)
                        atomic_json(runtime / ('apply-' + str(uuid.uuid4()) + '.json'), result)
                        return self.json_response({'receipt': result, 'source': next_data},
                                                  409 if result['result'] == 'stopped' else 200)
                    return self.json_response({'error': 'Unknown replay action'}, 404)
            except (ValueError, KeyError, AssertionError, OSError, URLError) as error:
                self.log_error('%s: %s', type(error).__name__, str(error))
                return self.json_response({'error': str(error),
                                           'next_action': 'Check the native platform, then refresh source evidence.'}, 502)

    assert feed.exists(), 'Create the faithful REST feed and native connectors before starting the bench'
    print(f'BidDelta bench http://127.0.0.1:{args.port}; queries -> {args.zetaris_url}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=APP.parent.parent)
    parser.add_argument('--zetaris-url', default='http://localhost:3000')
    parser.add_argument('--port', type=int, default=18086)
    serve(parser.parse_args())
