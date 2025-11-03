from fabric import Application
from fabric.utils import get_relative_path
from modules.window import AppWindow
from plugins.registry import PLUGINS_REGISTRY


window: AppWindow
app: Application


def set_css(app: Application):
    app.set_stylesheet_from_file(
        get_relative_path("index.css"),
    )


def use_plugin(plugin_name: str, **kwargs):
    global window

    plugin = PLUGINS_REGISTRY.get(plugin_name)
    if not plugin:
        return
    plugin.run(window=window, **kwargs)


def main():
    global app, window

    window = AppWindow()
    app = Application(
        window,
        name="fafafa",
    )

    set_css(app=app)

    app.run()


if __name__ == "__main__":
    main()
