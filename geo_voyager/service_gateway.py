from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from .dataset_graph import DatasetGraph
from .fetch_gateway import NoRedirect, make_handler as dataset_handler
from .service_graph import ServiceGraph
from .services import HTTP_USER_AGENT

MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 15


def allowed_request(protocol: str, path: str, method: str) -> bool:
    if protocol == 'taginfo':
        return method == 'GET' and path.startswith('/api/4/')
    if protocol == 'nominatim':
        return method == 'GET' and path in ('/search', '/reverse', '/lookup', '/status', '/details')
    if protocol == 'overpass':
        return path == '/api/interpreter' or (method == 'GET' and path == '/api/status')
    if protocol == 'valhalla':
        return path in ('/route', '/locate') or (method == 'GET' and path == '/status')
    return protocol == 'sparql' and path in ('/geo/sparql', '/geo/query')


def make_handler(graph: ServiceGraph, datasets: DatasetGraph | None = None):
    class ServiceHandler(dataset_handler(datasets if datasets is not None else DatasetGraph())):
        def do_GET(self):
            if self.path.startswith('/datasets/'):
                super().do_GET()
            else:
                self._call('GET')

        def do_HEAD(self):
            if self.path.startswith('/datasets/'):
                super().do_HEAD()
            else:
                self.send_error(405)

        def do_POST(self):
            self._call('POST')

        def _deny_method(self):
            self.send_error(405, 'Only registered read-only GET/POST operations are allowed')

        do_PUT = do_PATCH = do_DELETE = do_CONNECT = do_OPTIONS = _deny_method

        def _call(self, method):
            target = urlsplit(self.path)
            path = unquote(target.path)
            if (target.scheme or target.netloc or target.fragment or '\\' in path or '%' in path
                    or '//' in path or any(part in ('.', '..') for part in path.split('/'))
                    or any(ord(char) < 32 for char in path)):
                self.send_error(400, 'Absolute URLs and path escapes are forbidden')
                return
            parts = path.split('/', 3)
            if len(parts) != 4 or parts[1] != 'services':
                self.send_error(404)
                return
            try:
                service = graph.get(parts[2])
            except KeyError:
                self.send_error(404, 'Service is not registered')
                return
            service_path = '/' + parts[3]
            if not allowed_request(service.protocol, service_path, method):
                self.send_error(405, 'Endpoint or method is not a registered read operation')
                return
            if any(key.lower() in ('url', 'endpoint', 'target', 'base_url', 'update')
                   for key, _ in parse_qsl(target.query)):
                self.send_error(400, 'URL overrides and updates are forbidden')
                return
            body = None
            headers = {'User-Agent': HTTP_USER_AGENT}
            if service.protocol == 'sparql':
                headers['Accept'] = 'application/sparql-results+json'
            if method == 'POST':
                if self.headers.get('Transfer-Encoding'):
                    self.send_error(400)
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    self.send_error(400)
                    return
                if length < 0 or length > MAX_REQUEST_BYTES:
                    self.send_error(413)
                    return
                content_type = self.headers.get('Content-Type', 'text/plain')
                media = content_type.split(';', 1)[0].strip().lower()
                allowed_media = ('application/x-www-form-urlencoded', 'text/plain')
                if service.protocol == 'sparql':
                    allowed_media = ('application/sparql-query', 'application/x-www-form-urlencoded')
                elif service.protocol == 'valhalla':
                    allowed_media = ('application/json',)
                if media not in allowed_media:
                    self.send_error(415)
                    return
                self.connection.settimeout(TIMEOUT_SECONDS)
                try:
                    body = self.rfile.read(length)
                except TimeoutError:
                    self.send_error(408)
                    return
                if len(body) != length:
                    self.send_error(400)
                    return
                if media == 'application/x-www-form-urlencoded' and any(
                        key.lower() in ('url', 'endpoint', 'target', 'base_url', 'update')
                        for key, _ in parse_qsl(body.decode('utf-8', errors='replace'))):
                    self.send_error(400)
                    return
                headers['Content-Type'] = content_type
            url = service.base_url.rstrip('/') + service_path
            if target.query:
                url += '?' + target.query
            req = Request(url, data=body, headers=headers, method=method)
            try:
                with build_opener(ProxyHandler({}), NoRedirect()).open(req, timeout=TIMEOUT_SECONDS) as response:
                    result = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(result) > MAX_RESPONSE_BYTES:
                        self.send_error(502, 'Service response exceeds limit')
                        return
                    self.send_response(response.status)
                    self.send_header('Content-Type', response.headers.get('Content-Type', 'text/plain; charset=utf-8'))
                    self.send_header('Content-Length', str(len(result)))
                    self.end_headers()
                    self.wfile.write(result)
            except HTTPError as error:
                error.close()
                self.send_error(502, 'Service request failed; redirects are forbidden')
            except TimeoutError:
                self.send_error(504, 'Service request timed out')
            except URLError:
                self.send_error(502, 'Service request failed')

    return ServiceHandler
