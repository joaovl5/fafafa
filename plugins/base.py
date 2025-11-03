from typing import Protocol

from modules.window import AppWindow


class BasePlugin(Protocol):
    def run(self, window: AppWindow, **kwargs) -> None: ...
