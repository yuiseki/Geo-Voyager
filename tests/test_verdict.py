import pytest

from geo_voyager.verdict import Verdict


def test_verdict_rejects_empty_text():
    with pytest.raises(ValueError):
        Verdict("")
