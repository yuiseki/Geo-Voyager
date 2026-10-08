"""実験専用: 登録済み行政区・駅 Parquet の署名付き配信先を明示検証する。"""

from dataclasses import replace
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from geo_voyager.fetch_gateway import NoRedirect


def _register_download(graph, dataset_id):
    dataset = graph.get(dataset_id)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(Request(dataset.data_url, method="HEAD"), timeout=30):
            return
    except HTTPError as error:
        try:
            if error.code != 302:
                raise
            location = error.headers.get("Location", "")
            content_hash = error.headers.get("X-Xet-Hash", "")
            target = urlsplit(location)
            if (target.scheme != "https" or target.netloc != "us.aws.cdn.hf.co"
                    or not target.path.startswith("/xet-bridge-us/")
                    or not content_hash or target.path.rsplit("/", 1)[-1] != content_hash
                    or target.fragment):
                raise ValueError("Unverified registered dataset download URL")
            graph.register(replace(dataset, data_url=location))
        finally:
            error.close()


def register_admin_download(graph):
    _register_download(graph, "yuiseki/jp-admin-2026-09")


def register_station_download(graph):
    _register_download(graph, "yuiseki/ekidata-jp")
