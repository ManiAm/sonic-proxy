
import time
import logging
import threading
import multiprocessing

import utility

log = logging.getLogger(__name__)


class HTTP_Proxy():

    def __init__(self):

        self.terminate = False
        self.monitor_thread = None
        self.process = None


    def stop(self):

        self.terminate = True

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join()

        if self.process and self.process.is_alive():
            self.process.join()

        log.info("HTTP proxy stopped.")


    def start(self, proxy_host="0.0.0.0", proxy_port=None, daemon=True):

        if not proxy_port:
            proxy_port = utility.get_open_port_local()
            if not proxy_port:
                return False, "cannot get an ephemeral port"

        self._setup_http_proxy(proxy_host, proxy_port, daemon)

        return True, proxy_port


    def _setup_http_proxy(self, proxy_host, proxy_port, daemon):

        log.info("Waiting for the HTTP proxy to come up...")

        event_ready = multiprocessing.Event()
        terminate_flag = multiprocessing.Value('b', self.terminate)

        self.monitor_thread = threading.Thread(target=self._monitor_terminate_flag,
                                               args=(terminate_flag,))
        self.monitor_thread.start()

        self.process = multiprocessing.Process(target=self._start_mitmproxy,
                                               args=(proxy_host, proxy_port, event_ready, terminate_flag))
        self.process.start()

        # Wait for the proxy to come up
        event_ready.wait()

        log.info("\nRemote HTTP proxy is available at (%s, %s)\n", proxy_host, proxy_port)

        if not daemon:
            self.process.join()


    def _start_mitmproxy(self, proxy_host, proxy_port, event_ready, terminate_flag):

        from http_proxy import ThreadedMitmProxy, Addon

        with ThreadedMitmProxy(Addon, event_ready, listen_host=proxy_host, listen_port=int(proxy_port)):

            while not terminate_flag.value:
                time.sleep(0.5)  # Keep the main thread running

            log.info("Shutting down http proxy on %s...", proxy_port)


    def _monitor_terminate_flag(self, terminate_flag):

        while True:

            if self.terminate:
                terminate_flag.value = self.terminate
                break

            time.sleep(0.5)
