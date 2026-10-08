import pytest

from geo_voyager.service import Service
from geo_voyager.service_graph import ServiceGraph
from geo_voyager.services import load_service_graph


def test_registered_self_hosted_services():
    graph = load_service_graph()
    assert {service.protocol for service in graph.all()} == {'overpass', 'nominatim', 'valhalla', 'taginfo', 'sparql'}
    assert len(graph.all()) == 5
    for service in graph.all():
        assert graph.get(service.id) == service
        assert service.description and service.base_url
    with pytest.raises(KeyError):
        graph.get('other.yuiseki.net')


def test_service_graph_registers_and_gets():
    service = Service('test', 'read-only endpoint', 'http://origin:8000', 'taginfo')
    graph = ServiceGraph()
    graph.register(service)
    assert graph.get('test') == service
    assert graph.all() == [service]


@pytest.mark.parametrize('id,url,protocol', [('', 'http://origin', 'taginfo'),
    ('test', 'file:///etc/passwd', 'taginfo'), ('test', 'http://user:pass@origin', 'taginfo'),
    ('test', 'http://origin?url=other', 'taginfo'), ('test', 'http://origin', 'unknown')])
def test_invalid_service_is_rejected(id, url, protocol):
    with pytest.raises(ValueError):
        Service(id, 'description', url, protocol)
