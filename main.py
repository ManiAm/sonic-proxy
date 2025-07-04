
import sys
import logging
import signal

from router_sonic import Router_Sonic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger(__name__)
router = None


def handle_sigint(sig, frame):

    log.info("Received Ctrl+C (SIGINT). Cleaning up...")
    if router:
        router.stop()
    sys.exit(0)


if __name__ == "__main__":

    signal.signal(signal.SIGINT, handle_sigint)

    router = Router_Sonic(host='192.168.122.76', username='admin', password='YourPaSsWoRd')

    status, output = router.connect()
    if not status:
        log.error("Cannot connect to sonic router: %s", output)
        sys.exit(1)

    pkg_list = [
        "pyyaml",                 # YAML file parsing
        "rich",                   # Pretty-printing logs and tables
        "requests>=2.25,<3.0",    # HTTP library
        "urllib3>=1.26,<2.0",     # Low-level HTTP client (used by requests)
        "scapy>=2.5,<3.0",        # Packet crafting and sniffing
        "psutil>=5.9,<6.0",       # System monitoring (useful for diagnostics)
        "flask>=2.2,<3.0",        # Lightweight web server (for testing APIs)
        "httpx>=0.24,<1.0"        # Modern async-compatible HTTP client
    ]

    status, output = router.install_python_package(pkg_list)
    if not status:
        log.error("install_python_package failed: %s", output)
        sys.exit(1)
