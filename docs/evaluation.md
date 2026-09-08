# Evaluation

What the detector gets right, what it still gets wrong, and how the numbers
were produced. Everything here comes out of `python3 src/evaluate.py`.

## What was wrong before

The first version decided everything from signal magnitude:

```
max > 19.62  -> fall
std < 0.08   -> inactivity
```

It was tested on three sessions, one per state, and got all three right. That
wasn't a result. The simulator had been written to produce values that landed
on the right side of those two thresholds, so the test was checking its own
assumptions back to itself.

Running the same logic against situations it hadn't been built around:

| Situation | What happened | What should happen |
|---|---|---|
| Someone asleep | std ~0.04, flagged as inactivity | no alert |
| Someone sitting still | std ~0.05, flagged as inactivity | no alert |
| Device knocked off a table | peak 26 m/s², flagged as a fall | no alert |

Three false alarms out of three, one of them an ambulance call. A device that
behaves like this gets unplugged within a fortnight.

The reason is that magnitude on its own can't separate these. "Still and fine"
and "still and collapsed" have almost the same variance. Nudging the 0.08
threshold just swaps false alarms for missed emergencies — you can't win it
that way.

## What replaced it

Two things that look at the shape of the signal instead of its size.

**Breathing.** A person lying completely still is still breathing, and that
leaves a slow periodic trace around 0.25 Hz. A device sitting on the floor
doesn't breathe — it just gives sensor noise. Measuring how much of the
signal's power sits in the breathing band tells you whether a person is even
there.

**Postural shifts.** Someone asleep turns over every few minutes. Someone
unconscious doesn't. Counting those little movements tells you whether the
person who's there can still move.

Put together:

| Breathing | Shifts | Impact | Verdict |
|---|---|---|---|
| yes | yes | no | resting, fine |
| yes | none | no | collapsed — alert |
| yes | — | yes | fall — alert |
| no | — | yes | device dropped, no alert |
| no | none | no | device not worn |

### How well the breathing signal separates

Mean breathing ratio, 40 sessions per state, 1200s each:

| State | Ratio |
|---|---|
| device_drop (after impact) | 0.053 |
| fall (after impact) | 0.902 |
| inactive_emergency | 0.929 |
| sitting_still | 0.763 |
| sleep | 0.814 |

A device reads about 0.05 and a person about 0.90 — a 17-fold gap. That's what
makes the fall-versus-drop call reliable rather than a coin toss.

## The thing that actually fixed the false alarms

Tuning the shift-detection settings got false alarms from 32% down to about
12%, and then stuck. Sweeping the observation window instead showed why:

| Session length | False alarms | Misses | Sleep classified right |
|---|---|---|---|
| 60s | 24.00% | 0.0% | 16% |
| 120s | 14.00% | 0.0% | 44% |
| 180s | 10.00% | 0.0% | 60% |
| 300s | 7.00% | 0.0% | 72% |
| 600s | 2.00% | 0.0% | 92% |
| 1200s | 0.00% | 0.0% | 100% |

It's not about the thresholds. It's about how long you watch. In the first
three minutes a sleeping person might genuinely not move, so nothing can tell
them apart from someone collapsed. Give it twenty minutes and the difference
becomes obvious, because the sleeper eventually shifts and the collapsed person
doesn't.

This is also why v1's unused `INACTIVITY_MINUTES = 30` was the right instinct
even though the code ignored it and looked at 60 seconds. So escalation now
waits for a 20-minute confirmation window before it raises an inactivity alert.

## Where it lands

40 sessions per state, 1200s each, 240 sessions, different seed every time.

| True state | none | fall | inactivity | device_lost | Right |
|---|---|---|---|---|---|
| normal | 40 | 0 | 0 | 0 | 100% |
| sleep | 40 | 0 | 0 | 0 | 100% |
| sitting_still | 40 | 0 | 0 | 0 | 100% |
| device_drop | 0 | 0 | 0 | 40 | 100% |
| inactive_emergency | 0 | 0 | 40 | 0 | 100% |
| fall | 0 | 40 | 0 | 0 | 100% |

**False alarms: 0.00%** (0 of 160 benign sessions)
**Misses: 0.00%** (0 of 80 emergencies)

That's one run. See below for what it looks like across several.

## The missed fall, and what it turned out to be

An earlier run missed one fall in 40. The cause was not what it first appeared,
and the first written explanation of it was wrong.

The free fall was present — samples 12021 to 12032, dipping to 1.99 m/s², well
under the 5.89 threshold. The impact followed one sample later. But the peak
reached only 19.41 m/s² against an impact threshold of 19.62, so `find_impact`
returned `None` at its first check, before the lookback window was ever
evaluated. Across 40 fall sessions the peaks ranged 19.41 to 26.89, median
22.91 — so this was a genuine tail case, not a boundary artefact.

19.62 m/s² (2G) comes from Bourke et al. (2007), derived from healthy adults
falling onto a hard floor in a lab. Peak magnitude scales with body mass, drop
height and surface hardness. A light, frail person going down onto carpet lands
softer than a heavy adult onto tile. Holding everyone to 2G means the falls the
system misses are those by the smallest and frailest users — precisely the
people it exists for.

The fix works forwards from each free-fall episode rather than backwards from
the largest peak, and accepts any deceleration past a lower floor. The free
fall is what makes it a fall; the peak only says how hard. This also fixes a
second flaw: the previous version could only ever detect one fall per session.

Miss rate went from 1.25% to 0.00%.

### Is this just tuning to the test?

Partly, and it should be read that way. The floor was chosen after seeing which
case failed. Two checks against that.

**It isn't knife-edge.** Any floor between 10.0 and 18.0 gives 0.00% misses on
this seed set; only at 19.62 does the miss reappear. The chosen value sits
mid-plateau rather than at an edge.

**It holds across seed sets.** Repeating with eight independent base seeds —
1200 sessions — gives 0.00% misses throughout, and a false alarm rate averaging
0.25%, range 0.00% to 1.00%. One sleep session in 25 triggers a false
inactivity alert on some seed sets. So the single-run 0.00% above is the
optimistic end; 0.25% is the honest figure.

Both checks are still simulation. Real validation means a public fall dataset
such as SisFall or MobiAct, and that has not been done.

## Read this before trusting any of the above

**It's all synthetic.** I wrote the simulator and the detector against the same
mental model, which is a milder version of the circular problem that made v1
meaningless. The duration curve is a solid finding because it reflects
something structural — you can't tell apart two states that haven't diverged
yet. The exact percentages won't carry over to real data.

**The thresholds are tuned on that synthetic data.** `SHIFT_STD_MIN = 0.04` and
the rest were picked by sweeping against simulated sessions. They're starting
points for real tuning, not settled values.

**Breathing detection might not survive real hardware.** It assumes a breathing
amplitude around 0.03 m/s² against a noise floor near 0.008. On a wrist-worn
device the breathing signal is much weaker than on the chest, and a cheap
sensor might not pick it up at all. If it can't, the whole approach needs
rethinking.

**No real fall data has been tested.** The Bourke et al. (2007) thresholds come
from published research, not from anything measured here.

## Next, in order

1. Validate against SisFall and MobiAct — real labelled falls and daily
   activity. Expect the numbers to get worse.
2. Chase the residual false alarm. One sleeping session in 25 still trips the
   inactivity path on some seed sets, which suggests the shift detector misses
   genuine movement occasionally rather than the sleeper truly lying still.
3. Check whether breathing is even detectable on a real wrist sensor before
   building anything else on top of it.
4. Only then think about a learned model. Right now this is threshold and
   spectral logic, and it's labelled as such.