import operator
from typing import Callable, Iterator

from fabric.utils import DesktopApp, get_desktop_applications, idle_add, remove_handler
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib, Gdk  # type: ignore :(

from shared import icons


class Runner(Box):
    _app_list: list[DesktopApp] | None = None

    def __init__(self, close_callback: Callable | None = None, **kwargs) -> None:
        super().__init__(
            name="runner",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self._arranger_handler: int = 0
        self._selected_index = -1  # Track the selected item index
        self._refresh_apps()  # Loads desktop apps
        self._close_callback = close_callback

        ### Viewport
        self.viewport = Box(name="viewport", spacing=4, orientation="v")

        ### Scrolled Window
        self.scrolled_window = ScrolledWindow(
            name="runner-scrolled-window",
            spacing=10,
            min_content_size=(450, 105),
            max_content_size=(450, 105),
            child=self.viewport,
        )

        ### Input Field
        self.input_entry = Entry(
            name="runner-input",
            placeholder="Search...",
            h_expand=True,
            ### Events
            # when text content changes
            notify_text=self._handle_input_update,
            # when user presses enter
            on_activate=lambda entry, *_: self._handle_input_activate(entry.get_text()),
            # when user presses any key (not just text)
            on_key_press_event=self._handle_input_press,
        )
        self.input_entry.props.xalign = 0.5  # type: ignore

        ### Input box
        self.input_box = Box(
            name="runner-header-box",
            spacing=10,
            orientation="h",
            children=[
                self.input_entry,
                Button(
                    name="runner-close-button",
                    child=Label(name="runner-close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close(),
                ),
            ],
        )

        self.runner_box = Box(
            name="runner-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.input_box,
                self.scrolled_window,
            ],
        )

        self._resize_viewport()

        self.add(self.runner_box)
        self.show_all()

    def open(self):
        self._refresh_apps()
        self._arrange_viewport()

        # Disable text selection when opening
        def clear_selection():
            # Make sure no text gets selected during open
            entry = self.input_entry
            if entry.get_text():
                pos = len(entry.get_text())
                entry.set_position(pos)
                entry.select_region(pos, pos)
            return False

        # Schedule a selection clear after GTK finishes rendering
        GLib.idle_add(clear_selection)

    def close(self):
        self.viewport.children = []
        self._selected_index = -1  # Reset selection
        if self._close_callback:
            self._close_callback()

    def _refresh_apps(self):
        self._app_list = get_desktop_applications()

    def _resize_viewport(self):
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )

    def _filter_apps(self, query: str) -> list[DesktopApp]:
        query = query.casefold()
        filtered = []
        if not self._app_list:
            self._refresh_apps()
            assert self._app_list
        for app in self._app_list:
            choices = (
                (app.display_name or "") + app.name + (app.generic_name or "")
            ).casefold()
            if query in choices:
                filtered += [app]
        return sorted(filtered, key=lambda app: (app.display_name or "").casefold())

    def _make_app_slot(self, app: DesktopApp, **kwargs) -> Button:
        button = Button(
            name="slot-button",
            child=Box(
                name="slot-box",
                orientation="h",
                spacing=10,
                children=[
                    Image(
                        name="app-icon",
                        pixbuf=app.get_icon_pixbuf(size=24),
                        h_align="start",
                    ),
                    Label(
                        name="app-label",
                        label=app.display_name or "Unknown",
                        ellipsization="end",
                        v_align="center",
                        h_align="center",
                    ),
                ],
            ),
            tooltip_text=app.description,
            on_clicked=lambda *_: (app.launch(), self.close()),
            **kwargs,
        )
        return button

    def _add_next_application(self, apps_iter: Iterator[DesktopApp]):
        if not (app := next(apps_iter, None)):
            return False
        self.viewport.add(self._make_app_slot(app=app))
        return True

    def _scroll_to_selected(self, button):
        def scroll():
            adj = self.scrolled_window.get_vadjustment()
            alloc = button.get_allocation()
            if alloc.height == 0:
                return False  # Retry if allocation isn't ready

            y = alloc.y
            height = alloc.height
            page_size = adj.get_page_size()
            current_value = adj.get_value()

            # Calculate visible boundaries
            visible_top = current_value
            visible_bottom = current_value + page_size

            if y < visible_top:
                # Item above viewport - align to top
                adj.set_value(y)
            elif y + height > visible_bottom:
                # Item below viewport - align to bottom
                new_value = y + height - page_size
                adj.set_value(new_value)
            # No action if already fully visible
            return False

        GLib.idle_add(scroll)

    def _move_selection(self, delta: int):
        children = self.viewport.get_children()
        if not children:
            return

        # starting selection from 0
        if self._selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self._selected_index + delta
        new_index = max(0, min(new_index, len(children) - 1))
        self._update_selection(new_index)

    def _update_selection(self, new_index: int):
        # Unselect current:
        if self._selected_index != -1 and self._selected_index < len(
            self.viewport.get_children()
        ):
            current_button = self.viewport.get_children()[self._selected_index]
            current_button.get_style_context().remove_class("selected")
        # Select new:
        if new_index != -1 and new_index < len(self.viewport.get_children()):
            new_button = self.viewport.get_children()[new_index]
            new_button.get_style_context().add_class("selected")
            self._selected_index = new_index
            self._scroll_to_selected(new_button)
        else:  # Invalid index!
            self._selected_index = -1

    def _handle_arrange_complete(self, should_resize: bool, query: str):
        if should_resize:
            self._resize_viewport()
        # Only auto-select first item if query exists
        if query.strip() != "" and self.viewport.get_children():
            self._update_selection(0)
        return False

    def _arrange_viewport(self, query: str = ""):
        if self._arranger_handler:
            remove_handler(self._arranger_handler)

        self.viewport.children = []
        self._selected_index = -1  # Clear selection when viewport changes

        filtered_apps_iter = iter(self._filter_apps(query=query))

        # ???
        if not self._app_list:
            self._refresh_apps()
            assert self._app_list
        should_resize = operator.length_hint(filtered_apps_iter) == len(self._app_list)

        # Lazily add app slots
        self._arranger_handler = idle_add(
            lambda apps_iter: self._add_next_application(apps_iter)
            or self._handle_arrange_complete(should_resize, query),
            filtered_apps_iter,
            pin=True,
        )

    def _handle_input_update(self, entry: Entry, *_):
        """Handle updates in the runner input"""
        text: str = entry.get_text()

        self._arrange_viewport(text)

    def _handle_input_activate(self, text):
        """Handle "pressing enter" in the runner input"""
        children = self.viewport.get_children()
        if not children:
            return

        # Only activate if we have selection or non-empty query
        if text.strip() == "" and self._selected_index == -1:
            return  # Prevent accidental activation when empty

        # Open selected index, or the first one
        selected_index = self._selected_index if self._selected_index != -1 else 0
        if 0 <= selected_index < len(children):
            children[selected_index].clicked()

    def _handle_input_press(self, widget, event):
        """Handle key presses inside the entry"""

        # Normal app mode behavior
        if event.keyval == Gdk.KEY_Down:
            self._move_selection(1)
            return True
        elif event.keyval == Gdk.KEY_Up:
            self._move_selection(-1)
            return True
        elif event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
