
## SONiC Management Interface (User-Mode Networking)

To launch the Sonic virtual machine using QEMU with user-mode networking:

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name sonic-vm \
    -drive file=./img-sonic/sonic-vs.img,media=disk,if=virtio,index=0 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server

Wait for the Sonic VM to boot up, then verify the management interface (eth0) configuration:

    admin@sonic:~$ ip addr show eth0

    2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
        link/ether 52:54:00:12:34:56 brd ff:ff:ff:ff:ff:ff
        inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic eth0
        valid_lft 86267sec preferred_lft 86267sec
        inet6 fec0::5054:ff:fe12:3456/64 scope site dynamic mngtmpaddr
        valid_lft 86267sec preferred_lft 14267sec
        inet6 fe80::5054:ff:fe12:3456/64 scope link
        valid_lft forever preferred_lft forever

Check the default route:

    admin@sonic:~$ ip route
    default via 10.0.2.2 dev eth0 metric 202

This confirms that the Sonic VM has received an IP address (10.0.2.15) from QEMU's built-in DHCP server, and routes traffic through the default NAT gateway (10.0.2.2). You can verify external connectivity:

    admin@sonic:~$ ping 8.8.8.8

    PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
    64 bytes from 8.8.8.8: icmp_seq=1 ttl=255 time=16.2 ms
    64 bytes from 8.8.8.8: icmp_seq=2 ttl=255 time=17.8 ms

Test DNS resolution:

    admin@sonic:~$ ping google.com

    PING google.com (142.250.191.46) 56(84) bytes of data.
    64 bytes from nuq04s42-in-f14.1e100.net (142.250.191.46): icmp_seq=1 ttl=255 time=1s
    64 bytes from nuq04s42-in-f14.1e100.net (142.250.191.46): icmp_seq=2 ttl=255 time=2s
    64 bytes from nuq04s42-in-f14.1e100.net (142.250.191.46): icmp_seq=3 ttl=255 time=2s

Check QEMU's user-mode network from the QEMU monitor:

    (qemu) info network
    hub 0
    \ hub0port1: user.0: index=0,type=user,net=10.0.2.0,restrict=off
    \ hub0port0: e1000.0: index=0,type=nic,model=e1000,macaddr=52:54:00:12:34:56

By default, QEMU's user-mode networking only supports outbound traffic. To allow host-to-VM connections (e.g., for SSH), use port forwarding. For example, you can forward port 3040 on the host to SSH port 22 by adding these two options:

    -netdev user,id=mgmt0,hostfwd=tcp::3040-:22 \
    -device e1000,netdev=mgmt0

Then, SSH to the VM from the host:

    ssh admin@localhost -p 3040

## SONiC Management Interface (Bridge Networking)

For full LAN-level integration (VM appears as a peer on your network), use QEMU with bridge networking.

Create and configure a Linux bridge on the host

    sudo ip link add br0 type bridge
    sudo ip link set br0 up

Identify your host’s primary network interface (e.g., `enp6s18`) and flush its address:

    sudo ip addr flush dev enp6s18

**Warning**: Flushing will disconnect your existing SSH sessions. Use a local terminal.

Add `enp6s18` to the bridge:

    sudo ip link set enp6s18 master br0
    sudo ip link set enp6s18 up

Acquire a new IP on the bridge:

    sudo dhclient br0

Verify bridge configurations:

    ifconfig br0

    br0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
            inet 192.168.2.105  netmask 255.255.255.0  broadcast 192.168.2.255
            inet6 fe80::ca6:faff:feb9:b04a  prefixlen 64  scopeid 0x20<link>
            ether bc:24:11:74:a5:9b  txqueuelen 1000  (Ethernet)
            RX packets 1457  bytes 215047 (215.0 KB)
            RX errors 0  dropped 8  overruns 0  frame 0
            TX packets 970  bytes 139286 (139.2 KB)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

Your host will now request an IP address from DHCP server, but through the bridge.

### Launch QEMU with bridge networking

Add the following options to your QEMU command:

    -netdev bridge,id=mgmt0,br=br0 \
    -device e1000,netdev=mgmt0

If you encounter the error:

    failed to parse default acl file `/etc/qemu/bridge.conf'
    qemu-system-x86_64: bridge helper failed

It means QEMU's default network bridge helper utility (`qemu-bridge-helper`) does not have permission to use `br0`. This helper is designed to allow users to safely connect VMs to pre-approved network bridges without requiring full administrative privileges. To do this, it relies on an ACL (Access Control List) configuration file located at /etc/qemu/bridge.conf. This file explicitly defines which bridges are permitted for use by QEMU through the `qemu-bridge-helper`.

Fix this by creating an access control file:

    sudo mkdir -p /etc/qemu
    echo "allow br0" | sudo tee /etc/qemu/bridge.conf
    sudo chmod 644 /etc/qemu/bridge.conf

Re-run your QEMU command. Once the Sonic VM boots, it should receive an IP from your LAN's DHCP server.

    admin@sonic:~$ ip addr show eth0

    2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 q0
        link/ether 52:54:00:12:34:56 brd ff:ff:ff:ff:ff:ff
        inet 192.168.2.160/24 brd 192.168.2.255 scope glo0
        valid_lft 3387sec preferred_lft 3387sec
        inet6 fe80::5054:ff:fe12:3456/64 scope link
        valid_lft forever preferred_lft forever

You can now SSH into the Sonic VM using its assigned IP from any device on the local network.

### Creating Persistent Bridge

By default, a manually created Linux bridge is non-persistent and will be lost after a reboot, as it only exists in memory. To make the bridge persist across reboots, you must define it in your system’s network configuration using tools like `systemd-networkd` or `Netplan` (commonly used on Ubuntu). If you're using Ubuntu or a system that uses Netplan, edit:

    sudo nano /etc/netplan/01-netcfg.yaml

Example configuration to set up a persistent `br0` with physical NIC `enp6s18`:

    network:
        version: 2
        renderer: networkd
        ethernets:
            enp6s18:
                dhcp4: no
        bridges:
            br0:
                interfaces: [enp6s18]
                dhcp4: yes

Apply the changes:

    sudo netplan apply

This ensures the bridge and its associations are re-established automatically on every boot.

## libvirt

libvirt is a virtualization management layer that provides a unified interface to manage different hypervisors like QEMU/KVM, Xen, and others. The libvirt daemon (libvirtd) is a background service that provides the main control point for managing hypervisors and virtual machines. It listens for API requests from clients like `virsh` and acts as a mediator between these clients and the hypervisors.

On Debian/Ubuntu-based systems, install libvirt by:

    sudo apt install libvirt-daemon-system

Make sure that libvirt daemon is up and running.

    sudo systemctl status libvirtd

One of the powerful features of libvirt is automatic network management. When installed, libvirt creates a default virtual network called `virbr0`, a NAT-based Linux bridge. This allows VMs to have basic internet access and inter-VM communication without exposing them directly to the physical network. Verify `virbr0` is created and active:

    ifconfig virbr0

    virbr0: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
            inet 192.168.122.1  netmask 255.255.255.0  broadcast 192.168.122.255
            ether 52:54:00:43:83:82  txqueuelen 1000  (Ethernet)
            RX packets 0  bytes 0 (0.0 B)
            RX errors 0  dropped 0  overruns 0  frame 0
            TX packets 0  bytes 0 (0.0 B)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

The `virbr0` acts like a small virtual router. It provides a DHCP server (via `dnsmasq`), which assigns IP addresses to virtual machines connected to it, typically in the 192.168.122.0/24 range. When the SONiC VM's management interface (eth0) is connected to `virbr0`, it receives an IP address automatically via DHCP and can reach the outside network through NAT. This setup is convenient for quickly bringing up VMs with external network access and isolation from the physical LAN.

Allow virbr0 in bridge ACL:

    sudo mkdir -p /etc/qemu
    echo 'allow virbr0' | sudo tee -a /etc/qemu/bridge.conf
    sudo chmod 644 /etc/qemu/bridge.conf

Run Sonic VM inside QEMU and connect it to `virbr0`:

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name sonic-vm \
    -drive file=./img-sonic/sonic-vs.img,media=disk,if=virtio,index=0 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server \
    -netdev bridge,id=mgmt0,br=virbr0 \
    -device e1000,netdev=mgmt0

Wait for Sonic VM to boot up and then check eth0 IP address:

    admin@sonic:~$ ip addr show eth0

    2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 0
        link/ether 52:54:00:12:34:56 brd ff:ff:ff:ff:ff:ff
        inet 192.168.122.76/24 brd 192.168.122.255 scope global dynamic eth0
        valid_lft 3578sec preferred_lft 3578sec
        inet6 fe80::5054:ff:fe12:3456/64 scope link
        valid_lft forever preferred_lft forever

You can simply ssh to the sonic VM:

    ssh admin@192.168.122.76
