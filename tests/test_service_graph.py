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


def test_the_taginfo_contract_says_how_to_list_the_values_of_a_key():
    """The fields and the paging below were checked against the self-hosted Taginfo. See integration/test_taginfo_contract.py."""
    from geo_voyager.services import load_service_graph
    text = load_service_graph().get('taginfo').description
    key_values = text[text.index('/api/4/key/values'):]
    for fact in ['key を受け取り', 'page', 'rp', '両方が必須', 'HTTP 412', 'sortname=count', 'sortorder=desc',
                 'value', 'count', 'fraction']:
        assert fact in key_values, fact
    assert 'count_all ではない' in key_values        # the field of search/by_value is not the field of key/values


def test_the_by_value_contract_is_unchanged():
    from geo_voyager.services import load_service_graph
    text = load_service_graph().get('taginfo').description
    assert '/api/4/search/by_value は query で値を部分一致検索し、JSON data 配列の key/value/count_all を返す' in text


def test_the_taginfo_contract_says_how_to_count_one_tag_exactly():
    """Checked against the self-hosted Taginfo: /api/4/tag/stats returns the count of type 'all'. search/by_value matches parts."""
    text = load_service_graph().get('taginfo').description
    assert '/api/4/tag/stats' in text and 'type が "all"' in text and '部分一致' in text


def test_the_valhalla_contract_says_how_to_ask_and_where_the_answer_is():
    """Checked against the self-hosted Valhalla. See integration/test_valhalla_contract.py."""
    text = load_service_graph().get('valhalla').description
    for part in ('POST', 'application/json', 'costing', 'pedestrian', 'trip', 'summary', 'length', 'time', '秒', 'routes'):
        assert part in text, part
