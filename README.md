# AI Care Alert

Movement monitoring for people who live alone, built around measuring how often
it gets things wrong.

**Status:** research prototype, synthetic data only. No hardware, no real
accelerometer data yet.

## The idea

An alert system for elderly, disabled or isolated people that can notice a fall
or a collapse without anyone pressing a button. The button-press model assumes
the person is conscious and able to react, which is exactly the case where it's
least likely to be true.

## What it isn't

There's no machine learning in here. Detection is threshold logic plus some
spectral analysis of the breathing band. An earlier version of this README
called it an "AI monitoring layer", which wasn't accurate, and I've corrected
it. A learned model might come later, once the current approach is tested
against real data. The project name is from before that correction.

## What this actually solves

False alarms. A system that calls the family every night gets switched off, and
once it's off it protects nobody — so the number that decides whether something
like this is usable isn't detection accuracy, it's the false alarm rate.

The first version used two magnitude thresholds. Tested against situations it
hadn't been built around, it failed all three:

| Situation | Old verdict | Should be |
|---|---|---|
| Asleep | inactivity alert | no alert |
| Sitting still | inactivity alert | no alert |
| Device knocked off a table | fall — ambulance called | no alert |

The current version separates these using two signals:

- **Breathing** — a motionless person still breathes, leaving a slow trace
  around 0.25 Hz. A dropped device gives only noise. Measured separation
  between the two: **0.053 vs 0.902**.
- **Postural shifts** — a resting person turns over now and then, an
  unconscious one doesn't.

## Results

240 sessions, 40 per state, fresh seed each time, 1200s each:

| | |
|---|---|
| False alarms | **0.00%** (0 of 160 benign sessions) |
| Misses | **0.00%** (0 of 80 emergencies) |

Across eight independent seed sets — 1200 sessions — misses stay at 0.00%
throughout, and false alarms average 0.25%, range 0.00% to 1.00%. One sleeping
session in 25 still trips the inactivity path on some seed sets. The single-run
figures above are the optimistic end of that range.

### The fall that was missed, and what it turned out to be

An earlier run missed one fall in 40. The cause was not the detection window,
as this README first said.

The free fall was there, one sample before the peak. But the peak reached only
19.41 m/s² against an impact threshold of 19.62, so the impact check returned
before the window was ever evaluated. Across 40 fall sessions the peaks ranged
19.41 to 26.89 — a genuine tail case, not a boundary artefact.

19.62 m/s² comes from Bourke et al. (2007), measured on healthy adults falling
onto a hard floor in a lab. Peak magnitude scales with body mass, drop height
and surface hardness, so a light, frail person going down onto carpet lands
softer. Holding everyone to that figure means the falls missed are those by the
smallest and frailest users — precisely the people this is for.

Detection now works forwards from each free-fall episode rather than backwards
from the largest peak. The free fall is what makes it a fall; the peak only says
how hard. That also fixed a second flaw: the previous version could only ever
detect one fall per session.

The floor was chosen after seeing which case failed, so read it with that in
mind. `docs/evaluation.md` sets out the sensitivity check and the multi-seed
range.

### What the duration sweep showed

The main thing I learned: false alarms come down to how long you watch, not how
you set the thresholds.

| Watched for | False alarms |
|---|---|
| 60s | 24.00% |
| 180s | 10.00% |
| 600s | 2.00% |
| 1200s | 0.00% |

In the first few minutes a sleeping person might not move at all, so nothing
can tell them apart from someone collapsed. So escalation waits for a 20-minute
confirmation window.

Full workings and limitations: [`docs/evaluation.md`](docs/evaluation.md)

## Escalation

| Situation | Who gets alerted |
|---|---|
| Inactivity detected | Family first |
| Fall confirmed, or no response | Family and emergency services together |

The escalation path is design intent. No integration with any healthcare
provider has been built or agreed.

## Running it

```bash
pip install -r requirements.txt

python3 src/simulate_movement.py        # per-state summary
python3 src/evaluate.py                  # full run
python3 src/evaluate.py --n 40 --duration 1200
```

On Windows use `python` instead of `python3` and `src\` instead of `src/`.

## Layout

```
src/simulate_movement.py   six synthetic movement states
src/detector.py            the alert logic
src/evaluate.py            confusion matrix, false alarm and miss rates
docs/system_design.md      intended architecture
docs/evaluation.md         results and limitations
```

## The states it simulates

| State | Alerts? | Why it's here |
|---|---|---|
| normal | no | walking about |
| sleep | no | still but fine — the main false alarm trap |
| sitting_still | no | still but fine |
| device_drop | no | impact with nobody attached |
| inactive_emergency | yes | collapsed, breathing, not moving |
| fall | yes | free fall, impact, person on the floor |

## Honest limitations

Every number here is from synthetic data. I wrote both the simulator and the
detector, so it's still partly circular — the duration finding should hold
because it's structural, but the exact percentages won't transfer to real data.
Breathing detection assumes a signal a cheap wrist sensor may not pick up. No
real fall data has been tested.

## Next

1. Validate against SisFall and MobiAct
2. Chase the residual false alarm — one sleeping session in 25 still trips the
   inactivity path on some seed sets, which points at the shift detector missing
   genuine movement rather than the sleeper truly lying still
3. Check breathing is detectable on real wrist hardware
4. Consider a learned model only after that

## Where the fall thresholds come from

Bourke, A.K., O'Brien, J.V., Lyons, G.M. (2007). Free fall 5.89 m/s², impact
19.62 m/s², 50 Hz sampling.

## Related work

Indian patent application IN202611062464 A1 (published, unexamined) —
*AI-enabled smart healthcare wearable bracelet for continuous real-time patient
monitoring and predictive health analytics*, on which I'm first-named inventor.

That's a separate piece of work: a physiological monitoring bracelet (heart
rate, SpO₂, ECG), not this accelerometer project. What connects them is the
same underlying problem — keeping sensor signal quality high and false alarms
low when continuously monitoring vulnerable people. The patent's specification
raises signal noise and false-alarm reduction as a core challenge (paragraph
28); this repository is where I've actually worked that problem with measured
results.

## Author

Bhumii Shah — [github.com/Bhumii-AI-IoT](https://github.com/Bhumii-AI-IoT)