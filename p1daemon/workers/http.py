import logging
from json import dumps
from multiprocessing import Process

from ..config import (
    address,
    port,
    EVCC_KEY,
)

from http.server import HTTPServer, BaseHTTPRequestHandler

log = logging.getLogger(__name__)

class _GetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        copy = {k:v for k,v in self.server.data.get(EVCC_KEY,{}).items()}
        self.wfile.write(dumps(copy).encode())

class _MyHttpServer(HTTPServer):
    def __init__(self, shared_dict):
        self.data = shared_dict
        super().__init__((address, port), _GetHandler)

class HttpWorker(Process):
    def __init__(self, shared_dict: dict):
        self.data = shared_dict
        self.server = _MyHttpServer(shared_dict)
        super().__init__()

    def run(self):
        self.server.serve_forever()
