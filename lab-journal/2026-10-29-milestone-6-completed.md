# Milestone 6 completed: the sensor's identity, and the application and identity logs

| | |
| --- | --- |
| **Time** | About 2 hours on 29 October 2026 — the second target, the sensor's server certificate, and the application and identity logs. |
| **CISSP domains** | 7 Security Operations · 5 Identity and Access Management · 3 Security Architecture and Engineering · 6 Security Assessment and Testing · 4 Communication and Network Security |
| **Lab at the start** | The first target's host journal reaching the SIEM on its own certificate ([that entry](2026-10-28-milestone-6-host-logs.md)). Still local: the second target's host log, the application's per-request security log, and the identity provider's logins. And the SIEM's log listener still presented a certificate with no name, so a forwarder could check the signing authority but not *which* server answered. |

This finishes the milestone the last entry opened: get every host, application and identity log off its own box and into the SIEM, and give the sensor an identity the senders verify.

## The second target, by a recipe now proven

The second target got its host journal to the SIEM the same way the first did —
a key made on the box and never moved, a signing request couriered out by the
workstation, a certificate signed by the lab's own authority and carried back,
and a one-way, logged firewall pinhole so a monitored host can reach the
sensor without being handed a route back into the lab. The first target was
the one I learned on; the second was twenty minutes of following my own notes.
That is the point of writing the notes.

One thing the second target taught me the hard way: a firewall rule added at the
command line is gone at the next reboot. I had opened the pinhole live, watched
the logs flow, and then rebooted the gateway on purpose — and the host went
silent, because the rule had never been written to the file the gateway loads at
boot. The fix was to put it in the file and prove it survives a reboot, not just
to make it work once. "It works now" and "it works after a reboot" are two
different claims, and only the second one is worth anything.

## A certificate the sensor can be known by

Until now the SIEM's log listener presented the same nameless certificate every
host shared. A forwarder set to verify would confirm the certificate was signed
by the lab's authority — but *any* host holding a signed certificate would pass.
Verify-the-signature is not verify-the-server. A host that had been given a
client certificate for its own logging could stand up a listener and collect
every forwarder's logs, and each forwarder would accept it.

So the listener got a certificate of its own, carrying the sensor's identity,
marked for server use, signed by the same authority. Then every forwarder was
told to check that identity, not only the signature.

I did not want to *claim* that control worked — I wanted to watch it fail on
purpose. So I put the old nameless certificate back on the listener and watched a
forwarder, now set to verify the name, refuse to send: a certificate verification
failure in its log, and nothing shipped. Then I restored the real one and it
flowed again. A control you have only ever seen succeed is a control you have not
tested. The failing case is the test.

## The application's own security log

The application on the second target writes a line for every request it answers
— which tenant asked, whether the tenant filter was on, which documents it
retrieved and *their* tenants, the answer it gave. That line is where a
cross-tenant leak shows up: a retrieved document whose tenant is not the asker's.
It is the most security-relevant log in the whole application, and it was sitting
in a file on the box, read by no one.

Getting it to the SIEM ran into a wall worth describing. The log lived under the
application account's home directory, and that directory was closed to everyone
but its owner. The log shipper runs as a throwaway system account with no
business in a user's home — and I did not want to open that home directory up
just to read one file inside it. The answer was to leave the directory's
permissions exactly as strict as they were and let the service manager, which
runs as root, expose only that one log directory, read-only, at a path the
shipper could reach. The permission problem got solved in the service definition,
not by loosening the thing that was correctly locked down.

## The identity provider's logins

The last gap was identity: who logged in to the monitoring stack, and who failed
to. The identity provider recorded every login and every failed login — but only
to its own container's log, in a binary format meant for the container runtime to
read back, not a plain file a shipper can follow. The events existed; they were
just trapped in a shape nothing could tail.

The fix was to route that one container's output to the host's own system
journal, where a shipper reads it with the same mechanism it already used for the
host's login records. A forwarder on the sensor itself — the one box that had
been shipping none of its own logs — now carries both the sensor's host
journal and the identity provider's login events into the SIEM. A deliberately
wrong password at the login page now lands in the SIEM within seconds: the
failure type, the client, the source address, the username tried.

One small, honest snag: the first time the forwarder started, the identity
provider wasn't writing to the journal yet, so the forwarder saved a "start from
here" marker that pointed at nothing. When the events finally arrived, it was
still looking for a marker that no longer existed, and read nothing. Clearing
that saved position and letting it re-anchor to the live end of the journal fixed
it. A log shipper that silently reads nothing is its own kind of silent failure —
the only way I caught it was that the search kept coming back empty when I knew an
event had just happened.

## What I learned

- **Verify the server, not just the signature.** A certificate signed by the
  right authority proves the holder was signed by it — not that it is the server
  you meant to reach. Checking the name closes the gap, and a certificate for the
  collector that carries its identity is what makes checking the name possible.
- **Prove a control by making it fail.** Putting the wrong certificate back and
  watching the forwarder refuse is worth more than any number of successful
  sends. If I cannot make it fail, I do not actually know it is on.
- **Fix the permission problem in the unit, not the filesystem.** A log the
  shipper could not reach stayed unreachable at the directory level; the service
  manager exposed just the one file it needed, read-only, and the strict
  permissions that were correct stayed correct.
- **The log you need is not always in a shape you can read.** The identity events
  were being written the whole time, into a binary container log nothing could
  tail. Moving them to the system journal — not writing a parser for a format
  built for something else — was the cheaper, sturdier answer.
- **"Works now" is not "works after a reboot," and "shipping" is not "shipping
  what you think."** A live firewall rule vanished on reboot; a shipper with a
  stale start-marker read nothing while looking healthy. Both were caught only by
  insisting on the end-to-end evidence, not the intermediate green light.

## What to read in the output

| Output | What it tells you |
| --- | --- |
| A forwarder logging a certificate-verification failure and sending nothing | it is checking the sensor's *name*, not just the signing authority — the control is on |
| A host log that reappears only after the firewall file is fixed, not after a live rule | the rule is persisted, and survives the reboot that proved the live one wasn't |
| An application request line with a retrieved document whose tenant isn't the asker's | a cross-tenant retrieval — the leak the application log exists to show |
| A failed-login event in the SIEM with its source address and the username tried | the identity provider's events are centralised, not trapped in a container log |
| A log search that stays empty when you know an event just happened | a silent shipper — a stale read position or a filter that matches nothing, not "no events" |

## Next

The milestone's coverage goal is met: host, application and identity logs are off
their boxes and in the SIEM, and the sensor has an identity its senders verify.
What is left is use, not plumbing — turning the application's request log into a
detection for cross-tenant retrieval, and the identity provider's failures into
one for password-guessing, now that both are searchable in one place.
