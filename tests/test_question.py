import pytest

from geo_voyager.question import Question


def test_question_rejects_empty_text():
    with pytest.raises(ValueError):
        Question("")
