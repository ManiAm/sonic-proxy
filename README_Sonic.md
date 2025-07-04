
# Running Sonic VM on QEMU

This guide describes how to deploy a SONiC (Software for Open Networking in the Cloud) virtual machine using QEMU on an x86_64 host running Ubuntu 20.04.6 LTS. The VM is executed in QEMU’s system emulation mode, with KVM acceleration enabled for improved performance.

## Prerequisites

Ensure that KVM is supported and enabled on the host system:

    sudo apt update
    sudo apt install -y cpu-checker
    sudo kvm-ok

Expected output for a KVM-capable system:

    /dev/kvm exists
    KVM acceleration can be used

Install QEMU system emulation:

    sudo apt install qemu-system

Verify QEMU installation:

    qemu-system-x86_64 --version
    QEMU emulator version 4.2.1 (Debian 1:4.2-3ubuntu6.30)
    Copyright (c) 2003-2019 Fabrice Bellard and the QEMU Project developers

## Sonic Image Sources

The [SONiC Azure Pipelines](https://sonic-build.azurewebsites.net/ui/sonic/Pipelines) portal hosts official CI/CD pipelines. Each pipeline is associated with a specific hardware platform (e.g., Broadcom, Mellanox, Marvell, Centec, Innovium, Virtual Switch). The portal allows you to monitor builds, access artifacts, and download images suitable for deployment and testing. There are three common ways to run SONiC:

- Option 1: Run SONiC with QCOW2 Image
- Option 2: Run SONiC Using ONIE Installer
- Option 3: Create a Bootable Installer Disk

### Option 1: Run Sonic with QCOW2 Image

Navigate to the VS (Virtual Switch) pipeline on the Sonic CI portal.

Find the master branch and click on the 'Build History'.

Select the latest successful build by clicking on 'Artifacts'.

Under artifacts, click on `sonic-buildimage.vs`.

Download the artifact: `target/sonic-vs.img.gz` (note the double quotes around the URL):

```bash
cd /tmp
wget -O sonic-vs.img.gz "https://example.com/path/to/sonic-vs.img.gz"
```

Extract the archive to get `sonic-vs.img`:

```bash
gunzip sonic-vs.img.gz
```

Validate the image:

    file sonic-vs.img
    sonic-vs.img: QEMU QCOW2 Image (v3), 17179869184 bytes

You can load the QCOW2 disk image directly into QEMU with the following invocation:

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name sonic-vm \
    -drive file=./img-sonic/sonic-vs.img,media=disk,if=virtio,index=0 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server

QEMU sets up a telnet server on your local machine (127.0.0.1) at port 9000. You can then connect to this server using a telnet client to interact with the serial console of the emulated machine:

    telnet 127.0.0.1 9000

When the login prompt appears, login with `admin`/`YourPaSsWoRd`.

**Running Sonic VM using libvirt**

For users leveraging libvirt, the official SONiC repository provides a pre-configured domain definition file: [sonic.xml](https://github.com/sonic-net/sonic-buildimage/blob/master/platform/vs/sonic.xml). This XML file describes the virtual machine configuration for the SONiC Virtual Switch (VS) platform. Before use, edit the XML file to:

- Update the disk path to the absolute location of your `sonic-vs.img` file.
- Comment out the "<qemu:commandline>" and "<apparmor>" sections if they cause compatibility issues with your host setup.

To create and launch the VM:

    virsh create <path/to/sonic/xml>

Once the VM is running, you can connect to its console via Telnet:

    telnet 127.0.0.1 7000

### Option 2: Run Sonic Using ONIE Installer

In the Sonic Image Azure pipeline you have access to `sonic-vs.bin` file. This file is not meant to be run directly as a VM disk image like a QCOW2 file. It contains a POSIX shell script wrapper, embedded compressed kernel + root filesystem and instructions for ONIE to extract and install the Sonic OS onto the virtual switch.

    file sonic-vs.bin
    sonic-vs.bin: POSIX shell script executable (binary data)

You can check the shell script header by:

    head -n 20 sonic-vs.bin

    #!/bin/sh

    #  Copyright (C) 2013 Curt Brune <curt@cumulusnetworks.com>
    #
    #  SPDX-License-Identifier:     GPL-2.0
    ...

To boot the .bin file, ONIE runs first and executes the .bin to install Sonic. ONIE (Open Network Install Environment) is a minimal Linux environment used by whitebox switches to discover and install NOSes like Sonic.

When the switch is powered on, ONIE is the first to boot. It initializes the hardware and brings up the network interfaces. ONIE uses network protocols to discover available NOS installers on the network. This typically involves sending out DHCP requests to obtain an IP address and configuration details, followed by downloading the installer via HTTP, TFTP, or other supported protocols. Once the NOS installer is downloaded, ONIE executes it, and the installer takes over to complete the NOS installation process.

Download `sonic-vs.bin` and `onie-recovery-x86_64-kvm_x86_64-r0.iso` files (note the double quotes around the URL):

```bash
cd /tmp
wget -O sonic-vs.bin "https://example.com/path/to/sonic-vs.bin"
wget -O onie-recovery-x86_64-kvm_x86_64-r0.iso "https://example.com/path/to/onie-recovery-x86_64-kvm_x86_64-r0.iso"
```

Create a 2 GB virtual disk image in qcow2 format. This will act as the VM’s hard drive.

    qemu-img create -f qcow2 sonic.qcow2 16G

CD to the folder that has the `sonic-vs.bin` image and start a HTTP server:

    python3 -m http.server 8080

Start the Sonic VM:

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name onie \
    -boot order=cd,once=d \
    -cdrom ./img-sonic/onie-recovery-x86_64-kvm_x86_64-r0.iso \
    -drive file=./img-sonic/sonic.qcow2,media=disk,if=virtio,index=0 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server

Note that we are using ONIE to load the sonic OS.

Connect to the Sonic VM:

    telnet 127.0.0.1 9000

In the GRUB menu, choose **ONIE: Embed ONIE**. Then choose: **ONIE: Install OS**.

Once you reach the ONIE prompt:

    ONIE:/ #

Stop the ONIE discovery:

    ONIE:/ # onie-stop

And start the NOS installation by:

    ONIE:/ # onie-nos-install http://192.168.2.105:8080/sonic-vs.bin

Wait for Sonic OS to come up. The default credential for login is `admin`/`YourPaSsWoRd`.

Sonic is now installed on the sonic.qcow2. You can shut down the VM, then boot directly from the qcow2 disk (no need to boot ONIE again).

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name sonic-vm \
    -drive file=./img-sonic/sonic.qcow2,media=disk,if=virtio,index=0 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server

### Option 3: Create a Bootable Installer Disk

When using Sonic ONIE installer image, we started a http server on the host and used `onie-nos-install` to download the Sonic .bin image. You can package the .bin file (`sonic-vs.bin`) into a bootable installer disk image (`sonic-installer.img`):

    fallocate -l 4096M ./sonic-installer.img // creating raw disk image
    mkfs.vfat ./sonic-installer.img // format it with FAT

    tmpdir=$(mktemp -d)
    sudo mount -o loop ./sonic-installer.img $tmpdir  // mount disk image
    sudo cp ./sonic-vs.bin $tmpdir/onie-installer.bin // copy sonic image
    sudo umount $tmpdir

By creating a disk image with a specific file system (like FAT), you ensure that the image is bootable. This is particularly important for systems like ONIE, which rely on the ability to boot from various types of media.

    file sonic-installer.img

    sonic-installer.img: DOS/MBR boot sector, code offset 0x58+2, OEM-ID "mkfs.fat", sectors/cluster 8, Media descriptor 0xf8, sectors/track 63, heads 255, sectors 8388608 (volumes > 32 MB), FAT (32 bit), sectors/FAT 8184, serial number 0x6066d2e, unlabeled

Start the sonic VM. Note that the sonic disk image is loaded as a drive.

    sudo qemu-system-x86_64 \
    -m 8192 \
    -name onie \
    -boot order=cd,once=d \
    -cdrom ./img-sonic/onie-recovery-x86_64-kvm_x86_64-r0.iso \
    -drive file=./img-sonic/sonic.qcow2,media=disk,if=virtio,index=0 \
    -drive file=./img-sonic/sonic-installer.img,if=virtio,index=1 \
    -nographic \
    -accel kvm \
    -serial telnet:127.0.0.1:9000,server

ONIE will be able to automatically detect the `onie-installer.bin` and install Sonic.

This method is also used by the official [build_kvm_image](https://github.com/sonic-net/sonic-buildimage/blob/master/scripts/build_kvm_image.sh) script in the Sonic repository. To invoke it yourselfe, go to the root of the sonic-buildimage repository. Invoke the `build_kvm_image` script.

    sudo ./scripts/build_kvm_image.sh \
    ./img-sonic/sonic.qcow2 \  # hard-disk
    ./img-sonic/onie-recovery-x86_64-kvm_x86_64-r0.iso \  # ONIE recovery ISO
    ./img-sonic/sonic-vs.bin \ # Installer
    16  # hard-disk size
