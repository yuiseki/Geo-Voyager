from urllib.error import HTTPError
from ..execution_failure import bounded_output
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from ..services import HTTP_USER_AGENT, load_service_graph


def call_service(service_id: str, *, path: str = '', params: dict[str, str] | None = None,
                 body: str | None = None, content_type: str | None = None) -> str:
    load_service_graph().get(service_id)
    parsed = urlsplit(path)
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or '%' in path
            or '\\' in path or '..' in path.split('/') or '//' in path):
        raise ValueError('Only a service-relative path is accepted')
    url = 'http://gateway:8000/services/' + quote(service_id, safe='') + '/' + path.lstrip('/')
    if params:
        url += '?' + urlencode(params, quote_via=quote)  # a space as %20: '+' is not read back as a space by every service
    headers = {'User-Agent': HTTP_USER_AGENT}
    if content_type:
        headers['Content-Type'] = content_type
    req = Request(url, data=body.encode('utf-8') if body is not None else None,
                  headers=headers, method='POST' if body is not None else 'GET')
    try:
        with urlopen(req, timeout=20) as response:
            return response.read().decode('utf-8')
    except HTTPError as error:
        try:
            diagnostic = bounded_output(error.read(8193))
            raise RuntimeError(f'Service {service_id} HTTP {error.code}: {diagnostic}') from None
        finally:
            error.close()
