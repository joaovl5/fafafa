# Warning: this code is trash, I'll rewrite this some time
import json
import webbrowser
import os
from enum import Enum
from collections.abc import Callable
from functools import partial
from typing import Any
from loguru import logger
from modules.runner.runner import RunnerConfig
from modules.window import AppWindow
from pathlib import Path


class QuickLinksMode(Enum):
    LIST = "list"
    MENU = "menu"
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"


class QuickLinksPlugin:
    # Constant for JSON file path - can be changed later
    LINKS_FILE = Path("quicklinks.json")

    def _load_links(self) -> dict[str, str]:
        """Load links from JSON file"""
        if not os.path.exists(self.LINKS_FILE):
            logger.error("quicklinks.json file not found!")
            return {}

        try:
            with self.LINKS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(
                f"Could not load links from {self.LINKS_FILE}, starting with empty links"
            )
            return {}

    def _save_links(self, links: dict[str, str]) -> None:
        """Save links to JSON file"""
        try:
            with self.LINKS_FILE.open("w", encoding="utf-8") as f:
                json.dump(links, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save links to {self.LINKS_FILE}: {e}")

    def _add_link(self, name: str, link: str, overwrite: bool = False) -> None:
        """Add a new link or update existing one"""
        links = self._load_links()

        if name in links and not overwrite:
            logger.warning(
                f"Link '{name}' already exists. Use overwrite=True to update."
            )
            return

        links[name] = link
        self._save_links(links)

        action = "Updated" if name in links else "Added"
        logger.info(f"{action} link '{name}': {link}")

    def _open_link(self, name: str) -> None:
        """Open a link by name in the default browser"""
        links = self._load_links()

        if name not in links:
            logger.error(f"Link '{name}' not found")
            return

        url = links[name]
        try:
            webbrowser.open(url)
            logger.info(f"Opened link '{name}': {url}")
        except Exception as e:
            logger.error(f"Failed to open link '{name}': {e}")

    def _remove_link(self, name: str) -> None:
        """Remove a link by name"""
        links = self._load_links()

        if name not in links:
            logger.warning(f"Link '{name}' not found")
            return

        del links[name]
        self._save_links(links)
        logger.info(f"Removed link '{name}'")

    def _get_links(self) -> dict[str, str]:
        """Get all links as a dict mapping names to URLs"""
        return self._load_links()

    def _input_prompt(
        self, window: AppWindow, callback: Callable[[str], Any], hint: str = ""
    ):
        def internal_cb(result: int | str):
            if isinstance(result, int):
                logger.error("Unexpected int value in input callback")
                return
            callback(result)

        window.show_runner(
            cfg=RunnerConfig(
                items={},
                submit_callback=internal_cb,
                input_hint=hint,
            )
        )

    def _select_prompt(
        self,
        window: AppWindow,
        choices: dict[int, str],
        callback: Callable[[int], Any],
        hint: str = "",
    ):
        def internal_cb(result: int | str):
            if isinstance(result, str):
                logger.error("Unexpected str value in select callback")
                return
            callback(result)

        window.show_runner(
            cfg=RunnerConfig(
                items=choices,
                submit_callback=internal_cb,
                input_hint=hint,
            )
        )

    def _ask_url_callback(self, url: str, name: str):
        self._add_link(name=name, link=url)

    def _ask_name_callback(self, window: AppWindow, name: str):
        self._input_prompt(
            window=window,
            hint="Enter link URL...",
            callback=partial(self._ask_url_callback, name=name),
        )

    def list_links(self, window: AppWindow, idx_to_names: dict[int, str]) -> None:
        def open_link_callback(result: int | str):
            if isinstance(result, str):
                logger.error("Unexpected str value in open link callback")
                return
            self._open_link(name=idx_to_names[result])

        window.show_runner(
            cfg=RunnerConfig(
                items=idx_to_names,
                submit_callback=open_link_callback,
                input_hint="Search apps...",
            )
        )

    def add_link(self, window: AppWindow):
        self._input_prompt(
            window=window,
            hint="Enter name for the link...",
            callback=partial(self._ask_name_callback, window=window),
        )

    def update_link(self, window: AppWindow, idx_to_names: dict[int, str]):
        self._select_prompt(
            window=window,
            choices=idx_to_names,
            hint="Select link to update...",
            callback=lambda idx: self._input_prompt(
                window=window,
                hint="Insert updated link URL...",
                callback=lambda url: self._add_link(
                    name=idx_to_names[idx], link=url, overwrite=True
                ),
            ),
        )

    def remove_link(self, window: AppWindow, idx_to_names: dict[int, str]):
        self._select_prompt(
            window=window,
            choices=idx_to_names,
            hint="Select link to remove...",
            callback=lambda idx: self._remove_link(name=idx_to_names[idx]),
        )

    def show_menu(self, window: AppWindow) -> None:
        choices = {
            i: v.value
            for i, v in enumerate(
                [
                    QuickLinksMode.ADD,
                    QuickLinksMode.REMOVE,
                    QuickLinksMode.UPDATE,
                    QuickLinksMode.LIST,
                ]
            )
        }

        self._select_prompt(
            window=window,
            choices=choices,
            hint="Select desired mode...",
            callback=lambda idx: self._select_prompt(
                window=window,
                choices=choices,
                callback=lambda x: print(idx, x),
            ),
        )
        # self._select_prompt(
        #     window=window,
        #     choices=choices,
        #     hint="Select desired mode...",
        #     callback=lambda idx: self.run(window=window, mode=choices[idx]),
        # )

    def run(
        self, window: AppWindow, *, mode: QuickLinksMode | str | None = None, **__
    ) -> None:
        """Shows QuickLinksPlugin, by default with a selector for all links

        Parameters
        ----------
        window : AppWindow - AppWindow instance to use
        mode : QuickLinksMode - one of list/add/update/remove. "list" will
                                list all links found. "add" will prompt
                                for a new link to add. "update" will ask
                                user to select link to change, "remove"
                                will prompt selection to remove a link.
                                The "menu" option will show a prompt to
                                let you pick between modes.
        """
        if isinstance(mode, str):
            mode = QuickLinksMode[mode.upper()]
        elif mode is None:
            mode = QuickLinksMode.LIST

        names_to_links = self._get_links()
        idx_to_names = {k: v for k, v in enumerate(names_to_links.keys())}

        match mode:
            case QuickLinksMode.LIST:
                self.list_links(window=window, idx_to_names=idx_to_names)
            case QuickLinksMode.ADD:
                self.add_link(window=window)
            case QuickLinksMode.UPDATE:
                self.update_link(window=window, idx_to_names=idx_to_names)
            case QuickLinksMode.REMOVE:
                self.remove_link(window=window, idx_to_names=idx_to_names)
            case QuickLinksMode.MENU:
                self.show_menu(window=window)
