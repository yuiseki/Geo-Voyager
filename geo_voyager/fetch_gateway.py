import hashlib
from http.server import BaseHTTPRequestHandler
import os
import re
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


def mirror_name(url: str) -> str:
    """The file name of a local copy of a pinned table URL. The URL names a revision, so the copy never goes stale."""
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


_RANGE = re.compile(r'bytes=(\d+)-(\d*)')


def make_handler(graph: DatasetGraph, tables: dict[tuple[str, str], str] | None = None, mirror_dir: str | None = None):
    """GET and HEAD of /datasets/<dataset id> (the dataset's data_url) and of /datasets/<dataset id>/<table> (a table
    the dataset references list, at its pinned URL: geo_voyager.dataset_tables.TABLE_URLS). Nothing else.

    A table whose pinned file has a copy in mirror_dir (named by mirror_name) is read from the copy. Through the Hub,
    each range read is a new connection to its CDN, about 1 s from here, and one filtered read takes a dozen."""
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
            copy = os.path.join(mirror_dir, mirror_name(url)) if mirror_dir and url else None
            if copy and os.path.isfile(copy):
                self._serve_copy(method, copy)
                return
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

        def _serve_copy(self, method, path):
            size = os.path.getsize(path)
            start, end = 0, size - 1
            match = _RANGE.fullmatch(self.headers.get("Range", "")) if method == "GET" else None
            if match:
                start = int(match.group(1))
                end = min(int(match.group(2)) if match.group(2) else size - 1, size - 1)
                if start > end:
                    self.send_error(416)
                    return
            self.send_response(206 if match else 200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if match:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if method == "GET":
                with open(path, "rb") as file:
                    file.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = file.read(min(remaining, 1 << 20))
                        self.wfile.write(chunk)
                        remaining -= len(chunk)

        def log_message(self, format, *args):
            pass

    return DatasetHandler
