#   http_proxy.py

import asyncio
import threading
import logging
from typing import Any, Callable

from mitmproxy import http
from mitmproxy.addons import default_addons, script
from mitmproxy.master import Master
from mitmproxy.options import Options

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Addon:

    def __init__(self, event_ready: threading.Event) -> None:

        self.event_ready = event_ready
        self.n_reponse = 0


    def running(self):

        # signal the parent to proceed
        self.event_ready.set()


    def response(self, flow: http.HTTPFlow) -> None:

        if flow.response:
            self.n_reponse += 1
            logger.debug("reponse %s", self.n_reponse)


class ThreadedMitmProxy(threading.Thread):

    def __init__(self, user_addon: Callable, event_ready: threading.Event, **options: Any) -> None:

        super().__init__()

        self.user_addon = user_addon
        self.event_ready = event_ready
        self.options = options
        self.loop = None
        self.master = None


    def run(self) -> None:

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.master = Master(Options(), event_loop=self.loop)

        # Replace the ScriptLoader with the user addon
        self.master.addons.add(
            *(
                self.user_addon(self.event_ready) if isinstance(addon, script.ScriptLoader) else addon
                for addon in default_addons()
            )
        )

        # Set the options after the addons since some options depend on addons
        self.master.options.update(**self.options)

        try:
            self.loop.run_until_complete(self.master.run())
        except Exception as e:
            logger.error("Error running mitmproxy: %s", e)


    def __enter__(self):

        self.start()
        return self


    def __exit__(self, *_):

        self.master.shutdown()
        self.join()
