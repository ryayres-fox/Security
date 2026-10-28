# Milestone 5: a full red-team baseline of my RAG lab, and what the test taught me about the lab

| | |
| --- | --- |
| **Time** | _To confirm — two days, 21 and 22 October 2026, mostly a long scan with checks in between._ |
| **CISSP domains** | 6 Security Assessment and Testing · 8 Software Development Security · 7 Security Operations · 3 Security Architecture and Engineering |
| **Lab at the start** | The RAG app on target-2, answering 10 of 10 honest questions. Its only guard is one sentence in the system prompt, the sentence [the indirect-injection entry](2026-10-19-milestone-5-indirect-injection.md) proved load-bearing. target-2 at 6 GB. squawk's `ai-probe` driving garak 0.17.1 from Kali; the Malcolm sensor mirroring the wire. |
| **Framework** | OWASP LLM01 Prompt Injection, LLM07 System Prompt Leakage, LLM10 Unbounded Consumption. MITRE ATLAS AML.T0051.000 (LLM Prompt Injection: Direct), AML.T0054 (LLM Jailbreak). NIST AI RMF function Measure. |

## The goal

[The indirect-injection entry](2026-10-19-milestone-5-indirect-injection.md)
tested one attack by hand: an instruction hidden in a retrieved document. Its
*Next* asked for an industry red-team tool beside the hand-built probes. This
is that: garak's standard probe families against the same app, every family
to the end, so the lab has a baseline to measure controls against.

## Method

squawk's `ai-probe` runs garak against the app's `/ask` endpoint and reads
garak's report. Four probe families, in plain words:

- **dan** — role-play prompts that ask the model to drop its rules.
- **promptinject** — a request that tries to replace the app's instruction
  with the attacker's.
- **latentinjection** — the attacker's instruction hidden inside a document
  the model is asked to work on (a translation, a résumé, a report).
- **sysprompt_extraction** — attempts to get the model to reveal its own
  system prompt.

Up to 256 prompts per probe, one answer each. The app answers with a fixed
seed at temperature 0, so the same prompt gets the same answer. garak's
detectors score each answer; "through" means the detector says the attack got
past the model.

## What happened

It took five runs and two days. Not because the app was hard to test: each
run stopped on a different property of the lab, and each stop was a finding.

1. **The full run stalled at 10:35 and sat there for six hours.** squawk
   reported it as partial, which was right. The cause came out later (below).
2. **A rerun skipped 502s** and finished three probes, then stopped on a
   `413`: the app's 16 KiB request cap refused a long prompt, and garak treats
   any 4xx as fatal.
3. **A rerun skipped 413 and 502** and finished two probes, then stopped on a
   300-second read timeout. target-2 got a code update before this run, so
   that each answer reports the seed and model that produced it.
4. **One probe per run** after that, so one fatal error could not cost the
   rest. Two finished overnight.
5. **The last probe was stopped by my own watchdog** after the Mac slept for
   9½ hours, and ran again the next morning.

| family | probe | through / scored | rate |
| --- | --- | --- | --- |
| dan | Ablation_Dan_11_0 (two detectors) | 124 / 127 · 108 / 127 | **97.6% · 85.0%** |
| dan | AutoDANCached | 3 prompts | too few to read |
| promptinject | HijackHateHumans · KillHumans · LongPrompt | 148 / 255 · 105 / 256 · 134 / 256 | **58.0% · 41.0% · 52.3%** |
| latentinjection | LatentJailbreak | 82 / 256 | **32.0%** |
| latentinjection | the other eight | 0 to 28 of 256 each | 0% to 10.9% |
| sysprompt_extraction | SystemPromptExtraction | 0 / 250 | **0%** |

Skipped prompts are not in the counts: 26 refused by the size cap (`413`) and
17 lost to a model timeout or crash (`502`), in the runs that produced results.

## What the runs found about the lab

**A 502 retried without end.** Three witnesses tell the same story. garak's
report stopped at 10:35:42. ollama's own log shows every generation after
that minute ending at exactly two minutes with a 500, which is the app's
120-second model timeout. Malcolm shows 121 requests from 10:35 to 16:28, all
`POST /ask`, all `502`, all 226 bytes: one prompt, sent again every two
minutes. garak retries a 5xx with no limit on tries, and the app sets no limit
on how long an answer may run. A reboot of target-2 at 16:27 ended it.

**The model server runs out of memory.** On 6 GB, `llama3.2:3b` rests at
2.9 GB, and under the attack prompts it peaked at 5.1 to 5.4 GB. The kernel
killed it 11 times; each kill cost one prompt and a reload, and the 502 skips
land on the same minutes. The model server's container has no memory limit,
so the kernel chose among everything on the box.

**The size cap works.** 26 long prompts were refused with `413` before the
model saw them. That is a control doing its job, and those prompts count as
refused at the door, not resisted.

**A sleeping Mac pauses the whole lab.** Three pauses: about 40 minutes, 23
minutes, and 9½ hours. Afterwards target-2 and the gateway read behind by the
length of the pause until time sync caught up, about six minutes each time.
Malcolm's chart shows the 40-minute pause as a gap in the 502s, which also
explained 41 minutes I could not account for from garak's own uptime.

## What I learned

- **One sentence in a system prompt is not a control against direct
  attacks.** The indirect-injection entry showed it was load-bearing against
  a hidden instruction in a document. Here, role-play and hijack prompts got
  through 41 to 98 percent of the time. Same guard, different attack,
  different answer.
- **How a test tool handles errors decides what it measures.** Retry without
  end turned one slow answer into a six-hour stall. Fatal-on-4xx turned a
  working control into a lost run. Skip-and-count, stated in the result, is
  the only one of the three that tells the truth.
- **Report partial as partial.** Every stopped run said which families had no
  results. A clean-looking summary from a run that stopped halfway would have
  been the worst outcome.
- **Three independent witnesses beat one.** The tool's report, the model
  server's log and the network sensor agreed on the minute. Any one of them
  alone would have been a guess.
- **The lab's capacity and clock are part of the measurement.** A 6 GB box
  turned attack traffic into crashes, and a paused VM turned an hour into a
  stall. Both are now checks I run before a long test.

## Honest limits

One model, one seed, one answer per prompt. garak picks its 256 prompts per
probe at random (its own seed was unset), so two runs of a probe do not send
the same prompts. Detectors are heuristics: "through" is garak's judgment,
not mine, and the two dan detectors disagree by 13 points. AutoDANCached ran
3 prompts. The 43 skipped prompts are untested. The first two runs used the
app code before the update and the rest used the update; the seed,
temperature and model did not change, so the answers are comparable, but it
is not one run.

## Next

- target-2 is now 8 GB (22 October, honest set 10/10), so the out-of-memory
  skips should stop.
- The controls, each measured before and after on the same probes, one per
  run: an output cap and a memory limit first (they stop the stalls and
  crashes), then an input screen and an output check (the ones that should
  move the 41 to 98 percent).
- Detection: a rule on the behaviour Malcolm showed, the same request
  repeated against nothing but errors, rather than on the scanner's name in
  `User-Agent`, which a real attacker would change.
