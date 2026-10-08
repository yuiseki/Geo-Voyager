import json

from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.services import load_service_graph
from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_tokyo23_gateway import docker
from integration.test_worker_image import WORKER_IMAGE


def test_sandbox_calls_gateway_but_cannot_reach_service_hosts():
    with network_topology(isolated=True, gateway_code=gateway_code(), worker_image=WORKER_IMAGE,
                          include_origin=False) as names:
        wait_for_gateway(names['gateway'])
        sandbox = DockerSandbox(image=WORKER_IMAGE, network=names['internal'])
        output = sandbox.run("from geo_voyager.control_primitives import call_service; "
                             "print(call_service('taginfo', path='/api/4/site/info'))")
        assert json.loads(output)['name']
        code = '''
import socket
hosts = ['overpass.yuiseki.net','nominatim.yuiseki.net','valhalla.yuiseki.net','taginfo.yuiseki.net']
for host in hosts:
    try:
        socket.create_connection((host,443), timeout=2)
    except OSError:
        print(host, 'direct access blocked')
    else:
        raise AssertionError(host + ' reached directly')
'''
        blocked = sandbox.run(code)
        assert blocked.count('direct access blocked') == 4
        worker = json.loads(docker('inspect', names['worker']))[0]
        assert set(worker['NetworkSettings']['Networks']) == {names['internal']}
        assert worker['Mounts'] == []
        print(output, blocked, flush=True)
