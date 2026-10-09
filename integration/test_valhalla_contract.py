"""The Valhalla contract the Generator is given has to stay true. This calls the self-hosted Valhalla.

It needs the network. If Valhalla can not be reached the test is skipped, because then nothing is known about it.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import pytest

from geo_voyager.services import HTTP_USER_AGENT, load_service_graph

SERVICE = load_service_graph().get('valhalla')
SHIBUYA_TO_SHINJUKU = [{'lat': 35.6580, 'lon': 139.7016}, {'lat': 35.6896, 'lon': 139.7006}]


def route(body: dict | None = None, query: str = ''):
    data = json.dumps(body).encode() if body is not None else None
    request = Request(f'{SERVICE.base_url}/route' + (f'?{query}' if query else ''), data=data,
                      headers={'User-Agent': HTTP_USER_AGENT, 'Content-Type': 'application/json'},
                      method='POST' if data else 'GET')
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read() or b'{}')
    except URLError:
        pytest.skip('Valhalla can not be reached')


def test_a_post_with_costing_returns_trip_summary_length_in_km_and_time_in_seconds():
    status, body = route({'locations': SHIBUYA_TO_SHINJUKU, 'costing': 'auto', 'units': 'kilometers'})
    assert status == 200 and 'trip' in body and 'routes' not in body
    summary = body['trip']['summary']
    assert body['trip']['units'] == 'kilometers' and 3 < summary['length'] < 7 and summary['time'] > 60


def test_pedestrian_is_a_costing():
    status, body = route({'locations': SHIBUYA_TO_SHINJUKU, 'costing': 'pedestrian', 'units': 'kilometers'})
    assert status == 200 and body['trip']['summary']['time'] > 1800     # about 48 minutes on foot


def test_a_json_parameter_with_spaces_as_plus_can_not_be_parsed():
    text = json.dumps({'locations': SHIBUYA_TO_SHINJUKU, 'costing': 'auto'})
    assert route(query=urlencode({'json': text}))[0] == 400                      # ', ' became ',+'
    assert route(query=urlencode({'json': text}, quote_via=quote))[0] == 200     # what call_service sends
