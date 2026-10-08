from .intent import Intent
from .observation import Observation


class Worker:
    def execute(self, intent: Intent) -> list[Observation]:
        return [Observation("調査対象は東京23区である")]
