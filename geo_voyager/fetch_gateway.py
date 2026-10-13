from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .dataset_graph import DatasetGraph


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


HUB_HOSTS = ("huggingface.co", "hf.co")


def _on_the_hub(url: str) -> bool:
    parts = urlsplit(url)
    host = parts.hostname or ""
    return parts.scheme == "https" and any(host == hub or host.endswith("." + hub) for hub in HUB_HOSTS)


class HubRedirect(HTTPRedirectHandler):
    """Follow only the Hub's own redirects (resolve/ to its CDN); refuse every other one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not (_on_the_hub(req.full_url) and _on_the_hub(newurl)):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_handler(graph: DatasetGraph, tables: dict[tuple[str, str], str] | None = None):
    """GET and HEAD of /datasets/<dataset id> (the dataset's data_url) and of /datasets/<dataset id>/<table> (a table
    the dataset references list, at its pinned URL: geo_voyager.dataset_tables.TABLE_URLS). Nothing else."""
    tables = tables or {}

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
            url = tables.get(tuple(dataset_id.rsplit("/", 1))) if dataset_id.count("/") >= 2 else None
            if url is None:
                try:
                    dataset = graph.get(dataset_id)
                except KeyError:
                    self.send_error(404, "Dataset or table is not registered")
                    return
                url = dataset.data_url or dataset.url
            headers = {}
            if method == "GET" and "Range" in self.headers:
                headers["Range"] = self.headers["Range"]
            request = Request(url, headers=headers, method=method)
            opener = build_opener(ProxyHandler({}), HubRedirect())
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
