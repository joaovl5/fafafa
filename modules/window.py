from fabric.widgets.wayland import WaylandWindow
from loguru import logger

from modules.runner.runner import Runner, RunnerConfig


class AppWindow(WaylandWindow):
    def __init__(self, **kwargs):
        super().__init__(
            name="app",
            layer="top",
            anchor="center",
            margin="-40 0 0 40px",
            keyboard_mode="none",
            exclusivity="none",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.runner = Runner(close_callback=self.hide_runner)
        self._is_runner_open = False

        self.add_keybinding("Escape", self.hide_runner)
        self.add(self.runner)

    def hide_runner(self, *_):
        self.hide()
        self.set_keyboard_mode("none")
        self._is_runner_open = False

    def show_runner(self, cfg: RunnerConfig):
        try:
            self.show_all()
            self.set_keyboard_mode("exclusive")
            self.runner.open(cfg=cfg)
            self.runner.input_entry.set_text("")
            self.runner.input_entry.grab_focus()
            self._is_runner_open = True
        except Exception:
            logger.exception("Exception when showing runner!")
