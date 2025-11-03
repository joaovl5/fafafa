from plugins.apps import AppsPlugin
from plugins.base import BasePlugin
from plugins.quick_links import QuickLinksPlugin


PLUGINS_REGISTRY: dict[str, BasePlugin] = {
    "apps": AppsPlugin(),
    "quick_links": QuickLinksPlugin(),
}
