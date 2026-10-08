from .service import Service


class ServiceGraph:
    def __init__(self) -> None:
        self._services: dict[str, Service] = {}

    def register(self, service: Service) -> None:
        self._services[service.id] = service

    def get(self, service_id: str) -> Service:
        return self._services[service_id]

    def all(self) -> list[Service]:
        return list(self._services.values())
