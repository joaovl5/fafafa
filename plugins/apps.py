from fabric.utils import DesktopApp, get_desktop_applications
from loguru import logger

from modules.runner.runner import RunnerConfig
from modules.window import AppWindow


class AppsPlugin:
    def _get_apps(self) -> list[DesktopApp]:
        return get_desktop_applications()

    def run(self, window: AppWindow, **__) -> None:
        apps_from_ids = {i: app for i, app in enumerate(self._get_apps())}
        app_names_from_ids = {
            i: app.display_name or "Unknown" for i, app in apps_from_ids.items()
        }

        def runner_callback(result: int | str):
            if isinstance(result, int):
                # result is a key from our map
                app = apps_from_ids[result]
                app.launch()
            else:
                # result is user-provided cmd, run it!
                # TODO: run cmd
                logger.warning(f"Attempting to run cmd: {result}")

        window.show_runner(
            cfg=RunnerConfig(
                items=app_names_from_ids,
                submit_callback=runner_callback,
                input_hint="Search apps...",
            )
        )
