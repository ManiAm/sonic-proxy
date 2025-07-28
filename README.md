
# Sonic-Proxy

sonic-proxy is a lightweight HTTP proxy service designed to run on the host system that manages a Sonic NOS virtual machine. Its primary purpose is to provide a controlled outbound connectivity path for applications and processes running inside the Sonic VM. These applications can use the proxy to access external resources such as public package repositories, REST APIs, and software update services, capabilities that are often restricted or firewalled in production or isolated switch environments.

This enables tasks like installing Python packages via pip, fetching software via apt, or retrieving configuration and telemetry data over HTTP. This setup is especially valuable in lab environments, CI/CD pipelines, and automated testbeds, where Sonic-based virtual switches require Internet access for development, testing, or integration workflows. In addition to basic connectivity, sonic-proxy can support a variety of advanced use cases:

- **Traffic inspection and debugging**: Capture and analyze HTTP traffic for troubleshooting and behavioral analysis.

- **Access control and filtering**: Enforce policies by blocking or modifying outbound requests based on headers, URLs, or content types.

- **Logging and auditing**: Record request metadata for compliance, telemetry, or forensic purposes.

- **Simulating a restricted network**: Intercept and redirect requests to simulate outages, network throttling, delay, or packet loss.

## Getting Started

The following documentation provides a step-by-step introduction to run Sonic VM in QEMU:

- [Running Sonic VM](./README_Sonic.md)
- [Configuring Management Interface](./README_Sonic_mgmt.md)

We assume you are running a single Sonic virtual machine inside QEMU, and that the management interface (eth0) is reachable from the host system. In this setup, you should be able to establish an SSH connection to the VM from the host. Here, "192.168.122.76" represents the IPv4 address assigned to the Sonic VM's eth0 interface, and port 22 is the default SSH port. If port forwarding has been configured on the host, then you should connect using the forwarded port instead.

    ssh admin@192.168.122.76 -p 22

The [main.py](./main.py) script demonstrates how to use the HTTP proxy to install a list of Python packages from within a Sonic virtual machine. To run the script, simply execute:

    python3 main.py

Under the hood, sonic-proxy leverages mitmproxy as an embedded Python-based proxy engine, running in [regular mode](https://docs.mitmproxy.org/stable/concepts/modes/#regular-proxy). This allows the Sonic VM to route HTTP and HTTPS traffic through a user-defined proxy endpoint. For example, an HTTPS request routed through the proxy using `curl` would look like:

    curl --remote-name https://sample/url \
         --proxy http://proxy_ip:proxy_port \
         --insecure \
         --location

In this scenario, `curl` detects that the target URL uses HTTPS and transparently establishes a secure connection through the proxy using the "HTTP CONNECT" method. This allows encrypted traffic to pass through the proxy while preserving end-to-end TLS security unless explicit interception is configured. The `--insecure` flag tells `curl` to skip certificate validation.
