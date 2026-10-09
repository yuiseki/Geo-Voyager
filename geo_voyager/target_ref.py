from dataclasses import dataclass


@dataclass(frozen=True)
class TargetRef:
    """A target of an Intent: a name to show, and a stable id to identify it by.

    The id is the key. The name is what a person reads, and it varies: one place can be '港区' in a Goal and
    '港区, 東京都, 日本' in a geocoder's answer. A TargetRef without an id is a name that has not been looked up yet.
    """
    name: str
    id_type: str | None = None
    id_value: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError('TargetRef name must not be empty')
        if (self.id_type is None) != (self.id_value is None):
            raise ValueError('TargetRef needs both id_type and id_value, or neither')
        if self.id_value is not None:
            object.__setattr__(self, 'id_value', str(self.id_value))
            if not self.id_type or not self.id_value.strip():
                raise ValueError('TargetRef id_type and id_value must not be empty')

    @property
    def resolved(self) -> bool:
        return self.id_value is not None

    @property
    def key(self) -> tuple[str, str] | None:
        return (self.id_type, self.id_value) if self.resolved else None

    def same_target(self, other: 'TargetRef') -> bool:
        """The same id means the same target, whatever the names. Without ids only the names can be compared."""
        if self.resolved and other.resolved:
            return self.key == other.key
        return not self.resolved and not other.resolved and self.name == other.name

    def display(self) -> str:
        return f'{self.name} ({self.id_type}={self.id_value})' if self.resolved else self.name

    def to_dict(self) -> dict:
        return {'name': self.name, 'id_type': self.id_type, 'id_value': self.id_value} if self.resolved else {'name': self.name}

    @classmethod
    def from_dict(cls, data: dict) -> 'TargetRef':
        return cls(data['name'], data.get('id_type'), data.get('id_value'))
