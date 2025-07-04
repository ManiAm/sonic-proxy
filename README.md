
# Sonic-Proxy

sonic-proxy is a lightweight HTTP proxy service designed to run on the host system that manages a SONiC NOS virtual machine. Its primary purpose is to provide a controlled outbound connectivity path for applications and processes running inside the SONiC VM. These applications can use the proxy to access external resources such as public package repositories, REST APIs, and software update services, capabilities that are often restricted or firewalled in production or isolated switch environments.

This enables tasks like installing Python packages via pip, fetching software via apt, or retrieving configuration and telemetry data over HTTP. This setup is especially valuable in lab environments, CI/CD pipelines, and automated testbeds, where SONiC-based virtual switches require Internet access for development, testing, or integration workflows. In addition to basic connectivity, sonic-proxy can support a variety of advanced use cases:

- **Traffic inspection and debugging**: Capture and analyze HTTP traffic for troubleshooting and behavioral analysis.

- **Access control and filtering**: Enforce policies by blocking or modifying outbound requests based on headers, URLs, or content types.

- **Logging and auditing**: Record request metadata for compliance, telemetry, or forensic purposes.

- **Simulating a restricted network**: Intercept and redirect requests to simulate outages, network throttling, delay, or packet loss.

## Getting Started

The following documentation provides a step-by-step introduction to run Sonic VM in QEMU:

- [Running Sonic VM](./README_Sonic.md)
- [Configuring Management Interface](./README_Sonic_mgmt.md)

We assume you are running a single SONiC virtual machine inside QEMU, and that the management interface (eth0) is reachable from the host system. In this setup, you should be able to establish an SSH connection to the VM from the host. Here, "192.168.122.76" represents the IPv4 address assigned to the SONiC VM's eth0 interface, and port 22 is the default SSH port. If port forwarding has been configured on the host, then you should connect using the forwarded port instead.

    ssh admin@192.168.122.76 -p 22

The [main.py](./main.py) script demonstrates how to use the HTTP proxy to install a list of Python packages from within a SONiC virtual machine. To run the script, simply execute:

    python3 main.py
