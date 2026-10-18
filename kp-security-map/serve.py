#!/usr/bin/env python3
"""Serve the atlas and keep it in step with SATP.

    python3 serve.py                 # http://127.0.0.1:8080, opens a browser
    python3 serve.py --port 9000     # another port
    python3 serve.py --host 0.0.0.0  # expose on the network (no browser launch)
    python3 serve.py --no-sync       # never touch the network

The server adds three small endpoints on top of the static files:

    GET  /api/satp/status    sync state, snapshot date, warnings
    GET  /api/satp/data      the current satp.json (no-cache)
    POST /api/satp/refresh   re-download the nine datasheets + districts

It also refreshes the snapshot automatically when it is older than twelve hours,
so a copy left running follows SATP as the datasheets are updated.
"""
import argparse, json, os, sys, threading, time, urllib.parse, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'satp.json')
sys.path.insert(0, os.path.join(HERE, 'tools'))

STATE = {'busy': False, 'last_error': None, 'last_run': None, 'stage': None, 'started': time.time()}
LOCK = threading.Lock()


def snapshot(quiet=True, districts=True):
    """Run the synchroniser once, guarding against concurrent runs."""
    with LOCK:
        if STATE['busy']:
            return False
        STATE['busy'] = True
        STATE['stage'] = 'starting'
    try:
        import satp_refresh
        satp_refresh.refresh(quiet=quiet, districts=districts)
        STATE['last_error'] = None
        STATE['stage'] = 'done'
    except Exception as exc:                                  # noqa: BLE001
        msg = str(exc) or exc.__class__.__name__
        if 'SSL' in msg or 'timed out' in msg or 'Name or service' in msg or 'Connection' in msg:
            msg = ('cannot reach satp.org from this machine (%s). Check the connection, a proxy, '
                   'or run the sync somewhere the portal is reachable.' % msg)
        STATE['last_error'] = msg
        STATE['stage'] = 'failed'
        print('SATP sync failed:', msg)
    finally:
        STATE['last_run'] = time.time()
        STATE['busy'] = False
    return True


def read_snapshot():
    try:
        with open(DATA, encoding='utf-8') as f:
            d = json.load(f)
    except Exception:                                         # noqa: BLE001
        return {}
    return {
        'as_of': d.get('as_of'),
        'fetched_at': d.get('fetched_at'),
        'fetched_by': d.get('fetched_by'),
        'warnings': d.get('warnings', []),
        'districts': len(d.get('districts') or {}),
        'series_loaded': len(d.get('province_data') or {}),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        if '/api/' in (self.path or ''):
            sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/satp/status':
            snap = read_snapshot()
            return self._json({
                'ok': bool(snap.get('fetched_at')),
                'busy': STATE['busy'],
                'stage': STATE.get('stage'),
                'fetched_at': snap.get('fetched_at'),
                'as_of': snap.get('as_of'),
                'districts': snap.get('districts', 0),
                'series_loaded': snap.get('series_loaded', 0),
                'warnings': snap.get('warnings', []),
                'last_error': STATE['last_error'],
                'server_seconds': round(time.time() - STATE['started']),
            })
        if path == '/api/satp/data':
            try:
                with open(DATA, 'rb') as f:
                    body = f.read()
            except FileNotFoundError:
                return self._json({'error': 'no snapshot'}, 404)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == '/api/satp/refresh':
            return self.do_POST()
        return super().do_GET()

    def do_POST(self):
        if self.path.split('?')[0] != '/api/satp/refresh':
            return self._json({'error': 'not found'}, 404)
        if STATE['busy']:
            return self._json({'started': False, 'busy': True})
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        want_districts = q.get('districts', ['1'])[0] not in ('0', 'false', 'no')
        threading.Thread(target=snapshot, kwargs={'quiet': True, 'districts': want_districts},
                         daemon=True).start()
        return self._json({'started': True, 'busy': True, 'districts': want_districts})

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--no-sync', action='store_true')
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()

    os.chdir(HERE)
    httpd = None
    port = a.port
    for candidate in range(a.port, a.port + 20):
        try:
            httpd = ThreadingHTTPServer((a.host, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        sys.exit('No free port between %d and %d.' % (a.port, a.port + 19))

    url = 'http://%s:%d/' % ('127.0.0.1' if a.host in ('0.0.0.0', '') else a.host, port)
    print('\n  Khyber Pakhtunkhwa Security Atlas · SATP')
    print('  serving %s' % HERE)
    print('  open    %s\n' % url)
    print('  endpoints: /api/satp/status · /api/satp/data · /api/satp/refresh')
    print('  Ctrl+C to stop.\n')

    if not a.no_sync:
        age = time.time() - os.path.getmtime(DATA) if os.path.exists(DATA) else 1e9
        if age > 12 * 3600:
            have = read_snapshot().get('districts', 0)
            print('  snapshot is older than 12 h — refreshing from SATP in the background')
            threading.Thread(target=snapshot,
                             kwargs={'quiet': True, 'districts': have == 0}, daemon=True).start()

    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  stopped.')
        httpd.shutdown()


if __name__ == '__main__':
    main()
