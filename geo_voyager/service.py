from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Service:
    id: str
    description: str
    base_url: str
    protocol: str

    def __post_init__(self) -> None:
        url = urlsplit(self.base_url)
        if not self.id.strip() or '/' in self.id or not self.description.strip():
            raise ValueError('Service id and description are required')
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username
                or url.password or url.query or url.fragment or url.path not in ('', '/')):
            raise ValueError('Service must have a fixed HTTP origin without credentials or path')
        if self.protocol not in ('overpass', 'nominatim', 'valhalla', 'taginfo', 'sparql'):
            raise ValueError('Unsupported service protocol')
