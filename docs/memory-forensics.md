# Reading a machine's memory

Disk forensics tells you what a machine *stored*. Memory forensics tells you what
it was *doing* — the running processes, the network connections, the code that
was injected and never touched disk, the command an attacker typed. Malware that
lives only in RAM is invisible to a disk image and to most agents; the memory
capture is often the only place it exists.

This is the workflow: **acquire the volatile thing first, prove which OS you're
reading, then walk the machine's live state from processes outward to network and
artifacts.** Written from practice with [Volatility](https://www.volatilityfoundation.org/),
the open-source standard — examples use Volatility 3 (current; auto-detects the OS)
with the Volatility 2 equivalents noted, since a lot of published material still
assumes 2.

---

## 1 · Acquire before you analyze — and don't analyze the original

Memory is the most volatile evidence on the machine: it changes every second the
box is running and it's gone the moment it powers off. So it comes **first** in
the order of volatility, before you touch the disk.

- **Capture RAM to a file** with a tool that runs from removable media and writes
  elsewhere — [WinPmem](https://github.com/Velocidex/WinPmem), DumpIt, or a
  hypervisor snapshot for a VM. Write the capture to an external drive, **never to
  the disk you're investigating** — writing to local disk overwrites the unallocated
  space you may need later.

  ```bash
  # from removable media, output to a mounted evidence drive
  winpmem.exe -o E:\case-0421_host12_20260819.raw
  ```

- **Hash it immediately, then work on a copy.** The `.raw` you carve strings from
  and the image you run plugins against are *copies*; the original is hashed,
  written down, and set aside. This is the same chain-of-custody discipline as any
  evidence — if you can't show the analyzed image matches the captured one, the
  findings don't hold up.

  ```bash
  sha256sum case-0421_host12_20260819.raw > case-0421_host12_20260819.sha256
  cp case-0421_host12_20260819.raw working.raw    # analyze the copy
  ```

- **Name the capture for the case, host, and date** — `case-0421_host12_20260819.raw`,
  not `memory.dmp`. You will have more than one, and a capture you can't attribute
  to a host and a moment is a capture you can't testify to.

> Keep a **raw** copy specifically. Some workflows (string carving, third-party
> carvers) want a flat raw image, while others want a crash dump; Volatility can
> convert between them, but if you only kept one format you may be re-acquiring
> from a machine that has since changed or gone dark.

## 2 · Prove which OS you're reading — get this wrong and every plugin lies

A memory image is just bytes; the analyzer needs to know the OS build to make
sense of them. **Volatility 3 auto-detects this** from a symbol table — no manual
step, and one less thing to get wrong. **Volatility 2 required you to pick a
"profile"** (e.g. `Win10x64_19041`) by hand, and *a wrong profile doesn't error —
it produces plausible-looking garbage.* That failure mode is the whole reason the
version note matters:

```bash
# Volatility 3 — identify the image (auto)
vol -f working.raw windows.info

# Volatility 2 — you had to find the profile first, then pass it to everything
vol.py -f working.raw imageinfo          # suggests profiles
vol.py -f working.raw --profile=Win10x64_19041 pslist
```

If you're on Volatility 2 and `imageinfo` is ambiguous, `kdbgscan` is more precise.
The lesson generalizes past this one tool: **an analysis that silently assumes the
wrong context returns confident wrong answers** — the same silent-failure the rest
of this repository keeps flagging, in a forensic key.

## 3 · Walk the live state — processes first, then outward

There's a natural order. Start with what was running, decide what's suspicious,
then explain *how* it's suspicious with network and injection evidence.

**Processes — what was running, and what was hiding.**

```bash
vol -f working.raw windows.pslist        # processes the OS admits to (walks the list)
vol -f working.raw windows.psscan        # processes found by scanning memory (finds unlinked/hidden)
vol -f working.raw windows.pstree        # parent/child — spot the wrong parent
```

The pairing is the point: `pslist` walks the OS's own process list, so malware
that unlinks itself from that list is *invisible* to it. `psscan` scans memory for
process structures directly and finds them anyway. **A process in `psscan` but not
`pslist` is hiding — that gap is a lead, not a bug.** In `pstree`, a shell or
LOLBin whose parent is a browser or an Office app is the classic
"macro spawned a payload" shape.

**Injection — code that never touched disk.**

```bash
vol -f working.raw windows.malfind       # injected/unbacked executable memory
vol -f working.raw windows.dlllist       # loaded DLLs per process
vol -f working.raw windows.ldrmodules    # DLLs hidden from the loader lists
```

`malfind` looks for executable memory regions that aren't backed by a file on
disk — the signature of injected shellcode. This is exactly the class of threat a
disk image cannot show you.

**Network — who it was talking to.**

```bash
vol -f working.raw windows.netscan       # sockets and connections in the capture
```

Map suspicious PIDs from the process step to their connections. A short-lived
process with an outbound connection to a raw IP on an odd port is a C2 candidate —
and the remote address is your first **IOC to pivot on**.

**Attacker actions — what they typed.**

```bash
vol -f working.raw windows.cmdline       # command line each process was launched with
vol -f working.raw windows.consoles      # console command history (interactive)
```

Command lines and console history often hand you the attack narrative directly —
the download cradle, the flags, the staging path.

## 4 · Pull the artifacts and pivot to IOCs

Once you know *which* process and *which* region, extract the evidence and turn it
into something the rest of the pipeline can use.

```bash
# carve strings from the raw image and hunt a suspected domain
strings -a -t d working.raw | grep -i 'suspicious-domain.example' > hits.txt

# dump the suspect process's memory and its mapped files for malware analysis
vol -f working.raw -o ./out windows.memmap --pid 4123 --dump
vol -f working.raw -o ./out windows.dumpfiles --pid 4123
```

The strings + `grep` pass is deliberately low-tech and it's often what breaks a
case open: a domain, a mutex, a Bitcoin address, a filename living in RAM. Every
hash, domain, IP, and filename you recover is an **IOC** — and the point of
recovering it is to make it *reusable*:

- Feed the dumped process to a sandbox for behavioural analysis — the
  **[malware-triage](malware-triage.md)** workflow picks up exactly here.
- Turn the recovered domain/hash into a **detection** so the *next* host that
  talks to it alerts on its own — see **[writing-detections.md](writing-detections.md)**.
- Record it in the incident timeline — **[incident-response.md](incident-response.md)**.

A single memory capture, worked this way, seeds the detection that catches the
next intrusion. That's the payoff: forensics that ends in a finding is a report;
forensics that ends in a **detection** is a control.

## The pre-flight checklist

- [ ] Captured RAM **first**, to external media, before touching the disk
- [ ] Hashed the original; analyzing a **copy**, not the evidence
- [ ] Capture named for **case + host + date**
- [ ] OS/profile confirmed (`windows.info`, or `imageinfo`/`kdbgscan` on Vol 2) —
  not assumed
- [ ] `pslist` **vs** `psscan` compared for hidden processes
- [ ] `malfind` run for injected, disk-less code
- [ ] Suspect PIDs mapped to `netscan` connections
- [ ] Every recovered hash/domain/IP/filename logged as an **IOC** and pushed to a
  detection

---

*Memory forensics is where "acquire the volatile thing first" stops being a slogan
and becomes an order of operations. For the hands-on version, the forensics lab in
[`stepping-stones.md`](stepping-stones.md) walks a capture end-to-end on a machine
you own; for what to *do* with the IOCs you recover, see
[`writing-detections.md`](writing-detections.md) and [`malware-triage.md`](malware-triage.md).*
