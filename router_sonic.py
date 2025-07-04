
import sys
import re
import logging
import textfsm
from netmiko import ConnectHandler
from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet

from router_base import Router_Base
from http_proxy_start import HTTP_Proxy

log = logging.getLogger(__name__)


class Router_Sonic(Router_Base):

    def __init__(self, host, username, password, port=22):

        super().__init__(host, username, password, port)

        pip_trusted_host_list = [
            'pypi.org',
            'pypi.python.org',
            'files.pythonhosted.org',
            'github.com',
            'codeload.github.com'
        ]

        pip_trusted_host_list = [f"--trusted-host {elem}" for elem in pip_trusted_host_list]
        self.pip_trusted_hosts = " ".join(pip_trusted_host_list)


    def connect(self):

        sonic_vs = {
            'device_type'         : 'linux',
            'host'                : self.host,
            'username'            : self.username,
            'password'            : self.password,
            'port'                : self.port,
            "global_delay_factor" : 3,
            "fast_cli"            : False
        }

        try:
            self.router_connect = ConnectHandler(**sonic_vs)
        except Exception as e:
            return False, str(e)

        return True, None


    def get_mgmt_ip(self, interface="eth0"):

        status, output = self.get_interface_info(interface)
        if not status:
            return False, output

        IP = output.get("Ip", None)
        if not IP:
            return False, f"No IP address assigned to {interface}"

        return True, IP


    def get_interface_info(self, interface):

        status, output = self.run_command(f"ip addr show {interface}")
        if not status:
            return False, output

        with open("textfsm/ip_address_show.textfsm") as template_file:
            fsm = textfsm.TextFSM(template_file)
            parsed_output = fsm.ParseText(output)

        result = [
            dict(zip(fsm.header, row)) for row in parsed_output
        ]

        if not result:
            return False, f"cannot find interface {interface} info"

        return True, result[0]


    def get_default_route(self):

        status, output = self.run_command("ip route | grep default")
        if not status:
            return False, output

        match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', output)
        if not match:
            return False, "Failed to extract default gateway IP"

        gateway_ip = match.group(1)

        return True, gateway_ip.strip()


    #########################
    ###### PIP Install ######
    #########################

    def install_python_package(self, pkg_list, all_users=False):

        status, output = self.__install_pip()
        if not status:
            return False, output

        package_list = [
            "wheel",
            "setuptools"
        ]

        package_list = package_list + pkg_list

        status, output = self.__install_python_packages(package_list, all_users=all_users)
        if not status:
            return False, output

        return True, None


    def __install_pip(self):

        status, output = self.run_command("python3 -m pip --version")
        if status: # pip is already installed
            return True, output

        log.info("PIP not found. Installing...")

        http_proxy = HTTP_Proxy()
        status, output = http_proxy.start()
        if not status:
            return False, f"http_proxy start failed: {output}"
        http_proxy_port = output

        status, output = self.get_default_route()
        if not status:
            return False, output
        gw_ip = output

        try:

            cmd = 'curl --remote-name https://bootstrap.pypa.io/get-pip.py'
            cmd += f' --proxy http://{gw_ip}:{http_proxy_port}'
            cmd += ' --insecure --location'

            status, output = self.run_command(cmd)
            if not status:
                return False, output

            # installing pip, wheel, and setuptools
            cmd = 'python3 get-pip.py'
            cmd += f' --proxy="http://{gw_ip}:{http_proxy_port}"'
            cmd += ' --user'
            cmd += f' {self.pip_trusted_hosts}'

            status, output = self.run_command(cmd)
            if not status:
                return False, output

            # double-check to see if pip is installed
            status, output = self.run_command("python3 -m pip --version")
            if not status:
                return False, output

            log.info("Sucsesfully installed PIP:\n%s", output.strip())

            return True, None

        finally:

            http_proxy.stop()


    def __install_python_packages(self, package_list, all_users):

        install_candidates = []

        for package in package_list:

            log.info("Getting information for '%s'...", package)

            pkg_name, pkg_spec = self.__tokenize_package(package)

            status, output = self.run_command(f"python3 -m pip show {pkg_name}")
            if not status:
                install_candidates.append(package)
                continue

            if not pkg_spec:
                continue

            match = re.search(r"Version: (.+)", output)
            if not match:
                return False, f"Cannot get the installed version of {pkg_name}: {output}"

            version_str = match.group(1).strip()

            try:
                installed_ver = Version(version_str)
            except InvalidVersion:
                return False, f"Invalid version format in pip show: {version_str}"

            spec_set = SpecifierSet(pkg_spec)
            if installed_ver not in spec_set:
                install_candidates.append(package)

        if not install_candidates:
            log.info("All packages are up to date!")
            return True, None

        log.info("\nInstalling missing packages: %s", install_candidates)

        http_proxy = HTTP_Proxy()
        status, output = http_proxy.start()
        if not status:
            return False, f"http_proxy start failed: {output}"
        http_proxy_port = output

        status, output = self.get_default_route()
        if not status:
            return False, output
        gw_ip = output

        try:

            source = " ".join(f"'{pkg}'" for pkg in install_candidates)

            cmd = 'python3 -m pip install'
            cmd += f' --proxy="http://{gw_ip}:{http_proxy_port}"'

            if not all_users:
                cmd += ' --user'

            cmd += f' {self.pip_trusted_hosts}'
            cmd += f' {source}'

            status, output = self.run_command(cmd)  # timeout=15*60
            if not status:
                return False, output

            return True, None

        finally:

            http_proxy.stop()


    def __tokenize_package(self, name):

        match = re.match(r'^([a-zA-Z0-9_\-]+)(.*)', name)
        if not match:
            log.error("Invalid package format: %s", name)
            sys.exit(2)

        pkg_name = match.group(1).strip()
        specifiers = match.group(2).strip().lstrip(';').lstrip()
        return pkg_name, specifiers if specifiers else None
