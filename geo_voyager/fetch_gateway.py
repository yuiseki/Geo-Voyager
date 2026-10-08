from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .dataset_graph import DatasetGraph


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def make_handler(graph: DatasetGraph):
    class DatasetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._fetch("GET")

        def do_HEAD(self):
            self._fetch("HEAD")

        def _deny_method(self):
            self.send_error(405, "Only GET and HEAD are allowed")

        do_POST = do_PUT = do_PATCH = do_DELETE = _deny_method

        def _fetch(self, method):
            path = urlsplit(self.path)
            if path.query or path.fragment or path.scheme or path.netloc:
                self.send_error(400, "Only a dataset id is accepted")
                return
            if not path.path.startswith("/datasets/"):
                self.send_error(404)
                return
            dataset_id = unquote(path.path.removeprefix("/datasets/"))
            try:
                dataset = graph.get(dataset_id)
            except KeyError:
                self.send_error(404, "Dataset is not registered")
                return
            headers = {}
            if method == "GET" and "Range" in self.headers:
                headers["Range"] = self.headers["Range"]
            request = Request(dataset.data_url or dataset.url, headers=headers, method=method)
            opener = build_opener(ProxyHandler({}), NoRedirect())
            try:
                with opener.open(request, timeout=10) as response:
                    body = response.read() if method == "GET" else b""
                    self.send_response(response.status)
                    for name in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                        if name in response.headers:
                            self.send_header(name, response.headers[name])
                    self.end_headers()
                    if method == "GET":
                        self.wfile.write(body)
            except HTTPError as error:
                error.close()
                self.send_error(502, "Upstream request failed; redirects are not followed")
            except (URLError, TimeoutError):
                self.send_error(502, "Upstream request failed")

        def log_message(self, format, *args):
            pass

    return DatasetHandler
