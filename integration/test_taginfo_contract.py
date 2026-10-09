"""The Taginfo contract the Planner and the Generator are given has to stay true. This calls the self-hosted Taginfo.

It needs the network. If Taginfo can not be reached the test is skipped, because then nothing is known about it.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from geo_voyager.services import HTTP_USER_AGENT, load_service_graph

SERVICE = load_service_graph().get('taginfo')


def call(path: str, **params):
    request = Request(f'{SERVICE.base_url}{path}?{urlencode(params)}', headers={'User-Agent': HTTP_USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, None
    except URLError:
        pytest.skip('Taginfo can not be reached')


def test_key_values_with_paging_lists_values_with_value_and_count_in_use_order():
    status, body = call('/api/4/key/values', key='cuisine', page=1, rp=3, sortname='count', sortorder='desc')
    assert status == 200 and set(body) >= {'data', 'page', 'rp', 'total'}
    assert [set(item) >= {'value', 'count', 'fraction'} for item in body['data']] == [True, True, True]
    counts = [item['count'] for item in body['data']]
    assert counts == sorted(counts, reverse=True) and len(body['data']) == 3
    assert all('count_all' not in item for item in body['data'])            # the field is count


def test_key_values_needs_both_page_and_rp():
    assert call('/api/4/key/values', key='cuisine')[0] == 412
    assert call('/api/4/key/values', key='cuisine', rp=3)[0] == 412
    assert call('/api/4/key/values', key='cuisine', page=1, rp=3)[0] == 200


def test_search_by_value_still_returns_count_all():
    status, body = call('/api/4/search/by_value', query='pizza', page=1, rp=2, sortname='count_all', sortorder='desc')
    assert status == 200 and all('count_all' in item for item in body['data'])


def test_tag_stats_gives_the_count_of_one_tag_as_the_count_of_type_all():
    status, body = call('/api/4/tag/stats', key='cuisine', value='ramen')
    assert status == 200
    everything = [item for item in body['data'] if item['type'] == 'all']
    assert len(everything) == 1 and everything[0]['count'] > 1000


def test_search_by_value_matches_a_part_of_the_value():
    status, body = call('/api/4/search/by_value', query='ramen', page=1, rp=10, sortname='count_all', sortorder='desc')
    assert status == 200 and any(item['value'] != 'ramen' and 'ramen' in item['value'] for item in body['data'])
