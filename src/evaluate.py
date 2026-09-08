# evaluate.py
# Runs the detector over a lot of sessions and reports how often it's wrong.
#
# v1 tested three sessions, one per state, got all three right, and that was
# reported as working. n=1 per class isn't a result.
#
# The number that actually matters here is the false alarm rate. An alert
# system that wakes the family up for nothing gets unplugged, and once it's
# unplugged it protects nobody. Detection accuracy is the easy half.
#
#   python3 src/evaluate.py
#   python3 src/evaluate.py --n 100
#   python3 src/evaluate.py --n 20 --duration 1800

import argparse
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "src")

from simulate_movement import simulate_movement, STATES
from detector import detect_alert, INACTIVITY_WINDOW_S

LEVELS = ["none", "fall", "inactivity", "device_lost"]


def run(n_per_state=40, duration=1200, base_seed=1000, verbose=True):
    """Generate sessions, run the detector, tally up the mistakes.

    Careful with `duration`. The detector deliberately won't raise an
    inactivity alert until INACTIVITY_WINDOW_S has passed, so if sessions are
    shorter than that window every emergency gets reported as a miss and it
    looks like the detector is broken. It isn't - it's waiting. Default
    matches the window for that reason.
    """
    if duration < INACTIVITY_WINDOW_S and verbose:
        print(f"WARNING: sessions are {duration}s but the confirmation window "
              f"is {INACTIVITY_WINDOW_S:.0f}s.")
        print(f"         Inactivity can't be confirmed in that time, so the "
              f"miss rate below is about")
        print(f"         the window setting, not accuracy. Use "
              f"--duration {int(INACTIVITY_WINDOW_S)} or more.\n")

    confusion = defaultdict(Counter)
    correct = Counter()
    feature_log = defaultdict(list)

    seed = base_seed
    for state in STATES:
        for _ in range(n_per_state):
            df = simulate_movement(state=state, duration=duration, seed=seed)
            alert, level, _, feats = detect_alert(df, return_features=True)
            seed += 1

            confusion[state][level] += 1
            if alert == STATES[state]["should_alert"]:
                correct[state] += 1

            for k, v in feats.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    feature_log[f"{state}.{k}"].append(v)

    benign = [s for s in STATES if not STATES[s]["should_alert"]]
    urgent = [s for s in STATES if STATES[s]["should_alert"]]

    false_alarms = sum(n_per_state - correct[s] for s in benign)
    misses = sum(n_per_state - correct[s] for s in urgent)

    results = {
        "n_per_state": n_per_state,
        "duration": duration,
        "confusion": confusion,
        "correct": correct,
        "false_alarms": false_alarms,
        "benign_total": n_per_state * len(benign),
        "misses": misses,
        "urgent_total": n_per_state * len(urgent),
        "false_alarm_rate": false_alarms / (n_per_state * len(benign)),
        "miss_rate": misses / (n_per_state * len(urgent)),
        "features": feature_log,
    }

    if verbose:
        report(results)

    return results


def report(r):
    n = r["n_per_state"]
    total = n * len(STATES)

    print(f"\nAI Care Alert - detector evaluation")
    print(f"{n} sessions per state, {r['duration']}s each, {total} total\n")

    header = f"{'true state':<20}" + "".join(f"{l:>13}" for l in LEVELS) + f"{'ok':>9}"
    print(header)
    print("-" * len(header))

    for state in STATES:
        row = f"{state:<20}"
        for level in LEVELS:
            row += f"{r['confusion'][state][level]:>13}"
        print(row + f"{correct_pct(r, state, n):>8}")

    print(f"\nshould NOT alert: {', '.join(s for s in STATES if not STATES[s]['should_alert'])}")
    print(f"SHOULD alert:     {', '.join(s for s in STATES if STATES[s]['should_alert'])}\n")

    print(f"False alarms : {r['false_alarm_rate']:>7.2%}  "
          f"({r['false_alarms']}/{r['benign_total']} benign sessions alerted)")
    print(f"Misses       : {r['miss_rate']:>7.2%}  "
          f"({r['misses']}/{r['urgent_total']} emergencies not alerted)")

    if r["miss_rate"] > 0:
        print("\n  ^ any miss at all is a problem for something meant to "
              "summon help.")

    # Worth printing because it shows *why* the fall/drop split works, rather
    # than just that it does.
    print("\nBreathing ratio by state:")
    for key in sorted(r["features"]):
        if "resp" in key:
            vals = r["features"][key]
            print(f"  {key:<44} {sum(vals) / len(vals):.4f}  (n={len(vals)})")


def correct_pct(r, state, n):
    return f"{r['correct'][state] / n:.0%}"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=40, help="sessions per state")
    p.add_argument("--duration", type=int, default=1200, help="session length in seconds")
    args = p.parse_args()

    run(n_per_state=args.n, duration=args.duration)