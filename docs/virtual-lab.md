# A virtual security lab — VirtualBox, Kali, and a target

The safest place to practice offensive tooling is a lab that cannot reach
anything real. This is the bring-up for one: a **Kali** machine and a
**deliberately-vulnerable target**, both in VirtualBox, on a network the host
controls and nothing else can. Two rules carry the whole thing — **host-only
networking** so the target is unreachable from the LAN, and **snapshots** so any
machine reverts to a known-good state in seconds.

It pairs with the scanning work in this repo: the [scanner strategy](scanner-strategy.md)
and the detection docs are the blue side; this is where you stand up something to
point them at. Only ever test systems you own or are explicitly authorized to.

---

## 1 · VirtualBox and the two machines

Install [VirtualBox](https://www.virtualbox.org/). Then build two VMs.

### Kali (the tooling machine)

- **On an x86 host** — the standard Kali installer VM boots normally; give it
  2+ vCPU, 4+ GB RAM, and 40+ GB disk.
- **On an Apple Silicon Mac** — use the **Kali ARM64** image, and expect the VM to
  drop to a UEFI shell on first boot instead of finding the bootloader. Recover it
  once, then make it permanent:
  1. At the UEFI shell, type `exit`.
  2. **Boot Maintenance Manager → Boot from File**.
  3. Descend into the **EFI** volume → **kali** → **grubaa64.efi**, and boot it.
  4. Back in **Boot Maintenance Manager → Boot Options**, add EFI as a new boot
     entry and move it to the top, so the VM boots straight to Kali next time.

### The target

The target is the point — a machine built to be broken into.

- **On an x86 host** — [**Metasploitable 2**](https://sourceforge.net/projects/metasploitable/)
  is the classic choice: it serves several vulnerable web apps on port 80 (DVWA,
  Mutillidae, phpMyAdmin, TWiki) plus many exposed services, so you get varied,
  *known* results. Add its `.vmdk` to a new Linux VM; log in `msfadmin` / `msfadmin`.
- **On Apple Silicon** — Metasploitable 2 is **x86-only and will not boot under
  ARM VirtualBox.** Use an architecture-independent target instead:
  [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/) or
  [DVWA](https://github.com/digininja/DVWA) run fine as containers on an ARM Kali
  guest, or emulate an x86 target with UTM/QEMU (correct, but slow). Pick the
  container route unless you specifically need Metasploitable's non-web services.

> Whatever the target, **never give it a bridged adapter.** It is insecure on
> purpose and must never be reachable from your real network. Host-only only —
> see §3.

## 2 · A Kali baseline you can clone

Build Kali once into a clean state, snapshot it, and clone that snapshot per
project rather than reinstalling.

- **Create a normal user with sudo** and work as that user; elevate with `sudo`
  (or `su -`) only when a step needs root.
- **Fully update, then reboot:**

  ```bash
  sudo apt update && sudo apt full-upgrade -y
  sudo reboot
  ```

- **Install the matching kernel headers** (guest additions and driver builds need
  them):

  ```bash
  sudo apt install -y linux-headers-$(uname -r)
  ```

- **Install VirtualBox Guest Additions** for a usable display, shared clipboard,
  and shared folders: from the VM menu insert the Guest Additions CD, copy its
  contents to a local folder, and run the installer from there. (Support is
  strongest on x86; on ARM some features vary.)
- **Shut down and take a dated snapshot** — name it with the date and what it is,
  e.g. `2026-08-21 clean base + tools`. This is your golden image: clone it for
  each new engagement so a broken experiment never costs you the setup.

## 3 · The isolation spine — networking and snapshots

This is the part that makes the lab safe rather than reckless.

- **One host-only network** joins Kali and the target, routed by the host and
  reaching nothing else:

  ```bash
  VBoxManage hostonlyif create                       # e.g. vboxnet0
  VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0
  # then in each VM: Settings → Network → Host-only Adapter → vboxnet0
  ```

  Both machines land on `192.168.56.0/24`. Read the target's address with
  `ifconfig` / `ip a`.
- **Optionally give Kali a second NAT adapter** so *it* can reach the internet for
  updates while the target stays isolated.
- **Snapshot the target at a clean, serving state** and revert to it between runs,
  so every test starts from the same baseline instead of yesterday's wreckage:

  ```bash
  VBoxManage snapshot "Target" take clean-serving --live
  VBoxManage snapshot "Target" restore clean-serving      # between runs
  ```

## 4 · The toolbench

Kali ships most of what you need; a few additions are worth setting up once in the
golden image.

- **Metasploit** — start the console with `msfconsole`, and turn on logging so a
  session is reviewable afterward:

  ```
  msf6 > set ConsoleLogging true
  msf6 > set SessionLogging true
  ```

  Session logs land in `~/.msf4/logs/sessions/`.
- **Discover** ([leebaird/discover](https://github.com/leebaird/discover)) — recon
  and reporting scripts that must run from their install directory:

  ```bash
  sudo git clone https://github.com/leebaird/discover /opt/discover/
  cd /opt/discover/ && ./update.sh
  ```

- **SMBExec** ([brav0hax/smbexec](https://github.com/brav0hax/smbexec)) — clone it
  where you keep tooling:

  ```bash
  git clone https://github.com/brav0hax/smbexec.git
  ```

- **Wireless drivers** — for an external adapter that supports monitor mode and
  injection (e.g. an RTL8812AU-based card), install the DKMS driver so it rebuilds
  across kernel updates:

  ```bash
  sudo apt install -y dkms wireless-tools realtek-rtl88xxau-dkms
  ```

## Safety recap

- **Host-only networking, always.** The target is meant to be vulnerable; keep it
  off any network that touches something real.
- **Snapshots are the undo button.** A golden Kali image to clone, a clean target
  snapshot to revert to — so a mistake costs seconds, not a rebuild.
- **Only your own targets.** Everything here is for machines you own or are
  authorized to test. That line is the whole difference between a lab and an
  incident.

---

*This lab is the practice ground for the rest of the repo: stand a target up here,
then work it with the tools in [stepping stones](stepping-stones.md) and the
[scanner strategy](scanner-strategy.md). The same discipline the scanning docs
insist on — isolate the blast radius, revert to a known state — is exactly what
host-only networking and snapshots give you.*
