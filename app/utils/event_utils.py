from typing import Callable, List


class EventHandler:
    def __init__(self):
        self.event_table: dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable):
        if event_name not in self.event_table:
            self.event_table[event_name] = []

        self.event_table[event_name].append(callback)

    def emit(self, event_name: str, *args, **kwargs):
        if self.event_table.get(event_name) is None:
            return

        for callback in self.event_table.get(event_name):
            callback(*args, **kwargs)
