#!/usr/bin/env python3
"""Minimal stdlib WebSocket client (RFC 6455) — local fallback for QA harnesses.

The sandbox lost the `websocket-client` PyPI package (no network to reinstall),
and every harness in this dir uses only:
    websocket.create_connection(url) -> ws
    ws.send(text) | ws.recv() -> str | ws.settimeout(t) | ws.close()
This module provides exactly that interface with correct handshake framing,
client-side masking, fragmentation reassembly, and ping/pong handling.
"""
import base64
import hashlib
import os
import socket
import struct
import urllib.parse

_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class _WS:
    def __init__(self, sock):
        self._sock = sock
        self._buf = b''

    def settimeout(self, t):
        self._sock.settimeout(t)

    def _fill(self, n):
        while len(self._buf) < n:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError('websocket closed by peer')
            self._buf += chunk

    def _read_frame(self):
        self._fill(2)
        b1, b2 = self._buf[0], self._buf[1]
        fin = b1 & 0x80
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        length = b2 & 0x7F
        off = 2
        if length == 126:
            self._fill(4)
            length = struct.unpack('!H', self._buf[2:4])[0]
            off = 4
        elif length == 127:
            self._fill(10)
            length = struct.unpack('!Q', self._buf[2:10])[0]
            off = 10
        if masked:
            self._fill(off + 4)
            mask = self._buf[off:off + 4]
            off += 4
        else:
            mask = None
        self._fill(off + length)
        payload = self._buf[off:off + length]
        self._buf = self._buf[off + length:]
        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return fin, opcode, payload

    def recv(self):
        parts = []
        while True:
            fin, opcode, payload = self._read_frame()
            if opcode == 0x8:  # close
                raise ConnectionError('websocket close frame')
            if opcode == 0x9:  # ping -> pong
                self._pong(payload)
                continue
            if opcode == 0xA:  # pong: ignore
                continue
            if opcode in (0x1, 0x0):  # text / continuation
                parts.append(payload)
                if fin:
                    return b''.join(parts).decode('utf-8', 'replace')
            elif opcode == 0x2:  # binary (unexpected for CDP): collect like text
                parts.append(payload)
                if fin:
                    return b''.join(parts).decode('utf-8', 'replace')

    def send(self, text):
        data = text.encode('utf-8') if isinstance(text, str) else bytes(text)
        mask = os.urandom(4)
        header = bytes([0x81])
        n = len(data)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack('!H', n)
        else:
            header += bytes([0x80 | 127]) + struct.pack('!Q', n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self._sock.sendall(header + mask + masked)

    def _pong(self, payload=b''):
        self._sock.sendall(bytes([0x8A, len(payload)]) + payload)

    def close(self):
        try:
            self._sock.sendall(b'\x88\x00')
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass


def create_connection(url, timeout=10):
    u = urllib.parse.urlparse(url)
    if u.scheme not in ('ws', 'wss'):
        raise ValueError('only ws:// and wss:// supported')
    host, port = u.hostname, u.port or (443 if u.scheme == 'wss' else 80)
    path = u.path or '/'
    if u.query:
        path += '?' + u.query
    key = base64.b64encode(os.urandom(16)).decode()
    sock = socket.create_connection((host, port), timeout=timeout)
    if u.scheme == 'wss':
        import ssl
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
    req = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n'
           'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n'
           'Sec-WebSocket-Version: 13\r\n\r\n' % (path, host, port, key))
    sock.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError('handshake failed: connection closed')
        resp += chunk
    status = resp.split(b'\r\n', 1)[0]
    if b'101' not in status:
        raise ConnectionError('handshake failed: %r' % status[:80])
    accept = hashlib.sha1((key + _GUID).encode()).digest()
    if base64.b64encode(accept) not in resp:
        raise ConnectionError('handshake failed: bad Sec-WebSocket-Accept')
    ws = _WS(sock)
    ws.settimeout(timeout)
    return ws
