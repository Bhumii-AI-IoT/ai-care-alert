# simulate_movement.py
# Fake accelerometer data for testing the detector.
#
# v1 had three states - normal, inactive, fall - and the detector got all
# three right. That looked like success but proved nothing, because the
# simulator was built to produce values that crossed the exact thresholds the
# detector checked for. The test couldn't fail.
#
# The three states added here are the ones that break it:
#     sleep          - still, but fine
#     sitting_still  - still, but fine
#     device_drop    - impact, but nobody fell
#
# These are where the false alarms come from in real products. A system that
# can't tell them apart from an actual emergency calls the family every night
# and gets switched off inside a fortnight.
#
# The trick the detector uses is breathing. Someone lying motionless still
# breathes, which shows up as a slow periodic wobble. A dropped device
# doesn't. And sleeping people shift position every few minutes, whereas
# someone unconscious doesn't move at all.

import numpy as np
import pandas as pd

SAMPLING_RATE = 50
GRAVITY = 9.81

# Bourke et al. 2007
FREE_FALL_THRESHOLD = 5.89
IMPACT_THRESHOLD = 19.62

RESP_RATE_HZ = 0.25      # ~15 breaths/min
RESP_AMPLITUDE = 0.030   # m/s2 - small, but measurable on a torso device
SENSOR_NOISE = 0.008     # noise floor of a device just lying there

# should_alert is the ground truth label evaluate.py checks against.
STATES = {
    "normal":             {"should_alert": False},
    "sleep":              {"should_alert": False},
    "sitting_still":      {"should_alert": False},
    "device_drop":        {"should_alert": False},
    "inactive_emergency": {"should_alert": True},
    "fall":               {"should_alert": True},
}


def _breathing(t, rng, amplitude=RESP_AMPLITUDE):
    # Jitter the rate per session, otherwise the detector locks onto one exact
    # frequency and looks better than it is.
    rate = np.clip(rng.normal(RESP_RATE_HZ, 0.04), 0.18, 0.34)
    return amplitude * np.sin(2 * np.pi * rate * t + rng.uniform(0, 2 * np.pi))


def _shifts(n, fs, rng, mean_gap_s):
    # Short bursts of movement - turning over in bed, adjusting in a chair.
    # This is what a collapsed person doesn't have.
    out = np.zeros(n)
    count = max(0, rng.poisson((n / fs) / mean_gap_s))

    for _ in range(count):
        start = rng.integers(0, max(1, n - int(1.5 * fs)))
        end = min(n, start + int(rng.uniform(0.4, 1.2) * fs))
        burst = rng.normal(0, rng.uniform(0.5, 1.6), end - start)
        out[start:end] += burst * np.hanning(end - start)  # taper the edges

    return out


def simulate_movement(state="normal", duration=180, fs=SAMPLING_RATE, seed=None):
    """One session of fake accelerometer data.

    Pass a different seed per session, otherwise every session is identical
    and you're back to testing one sample per class.
    """
    if state not in STATES:
        raise ValueError(f"unknown state '{state}', try one of {list(STATES)}")

    rng = np.random.default_rng(seed)
    n = int(duration * fs)
    t = np.linspace(0, duration, n)

    if state == "normal":
        # Walking. 1.8 Hz is roughly average cadence.
        x = 0.8 * np.sin(2 * np.pi * 1.8 * t) + rng.normal(0, 0.40, n)
        y = 0.6 * np.sin(2 * np.pi * 1.2 * t) + rng.normal(0, 0.30, n)
        z = GRAVITY + 0.5 * np.sin(2 * np.pi * 0.9 * t) + rng.normal(0, 0.30, n)

    elif state == "sleep":
        # Motionless most of the time, breathing, turns over every ~4 min.
        x = rng.normal(0, 0.020, n) + _breathing(t, rng) * 0.4
        y = rng.normal(0, 0.020, n) + _breathing(t, rng) * 0.4
        z = GRAVITY + rng.normal(0, 0.018, n) + _breathing(t, rng)
        s = _shifts(n, fs, rng, mean_gap_s=240)
        x += s
        z += s * 0.6

    elif state == "sitting_still":
        # Watching telly. Still, but fidgets more often than someone asleep.
        x = rng.normal(0, 0.035, n) + _breathing(t, rng) * 0.5
        y = rng.normal(0, 0.035, n) + _breathing(t, rng) * 0.5
        z = GRAVITY + rng.normal(0, 0.030, n) + _breathing(t, rng)
        s = _shifts(n, fs, rng, mean_gap_s=45)
        x += s
        y += s * 0.5

    elif state == "inactive_emergency":
        # Collapsed. Still breathing, but no postural shifts at all - that
        # absence is the only thing separating this from sleep.
        x = rng.normal(0, 0.018, n) + _breathing(t, rng) * 0.4
        y = rng.normal(0, 0.018, n) + _breathing(t, rng) * 0.4
        z = GRAVITY + rng.normal(0, 0.016, n) + _breathing(t, rng)

    elif state in ("fall", "device_drop"):
        human = state == "fall"

        # Both start from movement - someone walking, or a device being
        # handled. Keeping the lead-up identical is deliberate: it forces the
        # detector to discriminate on what happens *after* the impact rather
        # than on some incidental difference beforehand.
        x = 0.8 * np.sin(2 * np.pi * 1.8 * t) + rng.normal(0, 0.40, n)
        y = 0.6 * np.sin(2 * np.pi * 1.2 * t) + rng.normal(0, 0.30, n)
        z = GRAVITY + rng.normal(0, 0.30, n)

        # Vary when it happens so the detector can't rely on timing.
        i0 = int(rng.uniform(0.15, 0.55) * duration * fs)

        # Free fall, ~200ms. Magnitude drops below 5.89.
        ff = int(rng.uniform(0.15, 0.28) * fs)
        x[i0:i0 + ff] = rng.normal(0, 1.5, ff)
        y[i0:i0 + ff] = rng.normal(0, 1.5, ff)
        z[i0:i0 + ff] = rng.normal(2.0, 1.0, ff)

        # Impact, ~100ms. Spikes above 19.62.
        i1 = i0 + ff
        imp = int(rng.uniform(0.06, 0.14) * fs)
        x[i1:i1 + imp] = rng.normal(12.0, 2.0, imp)
        y[i1:i1 + imp] = rng.normal(8.0, 2.0, imp)
        z[i1:i1 + imp] = rng.normal(15.0, 2.0, imp)

        # Everything above is identical for both. Only the aftermath differs.
        i2 = i1 + imp
        rest = n - i2

        if rest > 0:
            tr = t[i2:]
            if human:
                # On the floor: breathing, the odd feeble movement.
                x[i2:] = rng.normal(0, 0.022, rest) + _breathing(tr, rng) * 0.4
                y[i2:] = rng.normal(0, 0.022, rest) + _breathing(tr, rng) * 0.4
                z[i2:] = GRAVITY + rng.normal(0, 0.020, rest) + _breathing(tr, rng)
            else:
                # Inert. Noise only, no breathing. It also lands at some
                # random angle, so gravity spreads across all three axes
                # instead of sitting neatly on z.
                tilt = rng.uniform(0, np.pi)
                roll = rng.uniform(0, 2 * np.pi)
                x[i2:] = GRAVITY * np.sin(tilt) * np.cos(roll) + rng.normal(0, SENSOR_NOISE, rest)
                y[i2:] = GRAVITY * np.sin(tilt) * np.sin(roll) + rng.normal(0, SENSOR_NOISE, rest)
                z[i2:] = GRAVITY * np.cos(tilt) + rng.normal(0, SENSOR_NOISE, rest)

    magnitude = np.sqrt(x ** 2 + y ** 2 + z ** 2)

    return pd.DataFrame({
        "time_s": t,
        "accel_x": x,
        "accel_y": y,
        "accel_z": z,
        "magnitude": magnitude,
    })


if __name__ == "__main__":
    print("Sample session per state\n")
    print(f"{'state':<20}{'mean':>9}{'max':>9}{'std':>9}   alert?")
    print("-" * 58)

    for st in STATES:
        m = simulate_movement(state=st, seed=1)["magnitude"]
        print(f"{st:<20}{m.mean():>9.3f}{m.max():>9.3f}{m.std():>9.4f}"
              f"   {STATES[st]['should_alert']}")

    print("\nNote sleep and sitting_still both sit below v1's 0.08 threshold,")
    print("and fall and device_drop have near-identical peaks. That's the bug.")