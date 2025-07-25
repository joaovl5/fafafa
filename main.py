from functools import partial
from fabric import Application
from fabric.utils import get_relative_path
from modules.window import AppWindow


window: AppWindow
app: Application


def set_css(app: Application):
    app.set_stylesheet_from_file(
        get_relative_path("index.css"),
    )


def main():
    global app, window

    window = AppWindow()
    app = Application(
        window,
        name="fafafa",
    )

    app.set_css = partial(set_css, app)
    app.set_css()

    app.run()


if __name__ == "__main__":
    main()
