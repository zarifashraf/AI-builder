from app.models.contracts import EventRecord
from app.services.storage import InMemoryStore


class EventBus:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def emit(self, event_name: str, payload: dict) -> None:
        self.store.append_event(EventRecord(event_name=event_name, payload=payload))
