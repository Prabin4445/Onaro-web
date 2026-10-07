#!/usr/bin/env python3
"""Worker-2 CDP harness: console-error collection + screenshots + eval, with timeouts."""
import json, socket, sys, time, urllib.request

class CDP:
    def __init__(self, port=9223):
        self.port = port
        targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'))
        page = next(t for t in targets if t['type'] == 'page')
        wsurl = page['webSocketDebuggerUrl']
        import websocket
        self.ws = websocket.create_connection(wsurl, timeout=12)
        self.ws.sock.settimeout(12)
        self.mid = 0
        self.errors = []  # console.error + pageerror + failed requests

    def send(self, method, params=None, timeout=12):
        self.mid += 1
        msg = json.dumps({'id': self.mid, 'method': method, 'params': params or {}})
        self.ws.send(msg)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                raw = self.ws.recv()
            except socket.timeout:
                raise RuntimeError(f'CDP timeout on {method}')
            data = json.loads(raw)
            if 'id' in data and data['id'] == self.mid:
                if 'error' in data:
                    raise RuntimeError(f'CDP error {method}: {data["error"]}')
                return data.get('result', {})
            # capture events
            if data.get('method') in ('Log.entryAdded', 'Runtime.consoleAPICalled',
                                      'Runtime.exceptionThrown', 'Network.loadingFailed'):
                self._note_event(data)
        raise RuntimeError(f'CDP no-response on {method}')

    def _note_event(self, data):
        m = data.get('method')
        if m == 'Log.entryAdded':
            e = data['params']['entry']
            if e.get('level') in ('error',):
                self.errors.append(f"LOG {e.get('level')}: {e.get('text','')[:300]}")
        elif m == 'Runtime.consoleAPICalled':
            if data['params']['type'] == 'error':
                args = [a.get('description') or a.get('value') for a in data['params']['args']]
                self.errors.append('CONSOLE: ' + ' '.join(str(a)[:300] for a in args))
        elif m == 'Runtime.exceptionThrown':
            d = data['params'].get('exceptionDetails', {})
            self.errors.append('PAGEERROR: ' + str(d.get('text') or d.get('exception', {}).get('description'))[:300])
        elif m == 'Network.loadingFailed':
            self.errors.append('REQFAIL: ' + data['params'].get('errorText','') + ' ' + data['params'].get('blockedReason',''))

    def enable_capture(self):
        self.send('Log.enable')
        self.send('Runtime.enable')
        self.send('Network.enable')

    def eval(self, js, timeout=12):
        r = self.send('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': True}, timeout=timeout)
        if 'exceptionDetails' in r:
            raise RuntimeError('EVAL exception: ' + json.dumps(r['exceptionDetails'])[:500])
        return r['result'].get('value')

    def drain(self):
        """Non-blocking drain of pending events."""
        old = self.ws.sock.gettimeout()
        self.ws.sock.settimeout(0.3)
        try:
            while True:
                try:
                    raw = self.ws.recv()
                except (socket.timeout, Exception):
                    break
                data = json.loads(raw)
                if 'method' in data:
                    self._note_event(data)
        finally:
            self.ws.sock.settimeout(old)

    def shot(self, path, full=False):
        if full:
            r = self.send('Page.captureScreenshot', {'captureBeyondViewport': True})
        else:
            r = self.send('Page.captureScreenshot')
        import base64
        open(path, 'wb').write(base64.b64decode(r['data']))

    def close(self):
        try: self.ws.close()
        except Exception: pass

def fresh(port=9223, url='file:///home/hatch/workspace/hub/index.html', clear_storage=True):
    c = CDP(port)
    c.enable_capture()
    # force 390x844 mobile viewport regardless of the real window size
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.navigate', {'url': url})
    time.sleep(1.5)
    if clear_storage:
        c.eval('localStorage.clear()')
        c.send('Page.reload')
        time.sleep(1.5)
    c.drain()
    return c

if __name__ == '__main__':
    c = fresh()
    c.drain()
    print('ERRORS:', c.errors)
    c.shot('/tmp/w2-smoke.png')
    c.close()
