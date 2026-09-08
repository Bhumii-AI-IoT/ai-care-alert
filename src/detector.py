# detector.py
# Alert logic for AI Care Alert.
#
# v1 used two rules on signal magnitude:
#     max > 19.62  -> fall
#     std < 0.08   -> inactivity
#
# Both fail badly. A sleeping person sits at std ~0.04, so every night set off
# an alert. And a device knocked off a table looks exactly like a human fall
# if all you measure is peak magnitude. Numbers in docs/evaluation.md.
#
# The fix is to stop asking how big the signal is and start asking what shape
# it has.

import numpy as np

SAMPLING_RATE = 50

# Fall phases, from Bourke et al. 2007.
FREE_FALL_THRESHOLD = 5.89
IMPACT_THRESHOLD = 19.62
FREE_FALL_LOOKBACK_S = 0.5

# How long after a free fall to keep looking for the landing.
IMPACT_SEARCH_S = 1.0

# Lower bound on what still counts as an impact when free fall came first.
#
# 19.62 (2G) is Bourke's figure and it's fine for the falls it was derived
# from - healthy adults, instrumented lab, hard floor. It is not fine as an
# absolute floor. Peak magnitude scales with body mass, drop height and how
# hard the surface is, so a light frail person going down onto carpet lands
# softer than a heavy adult onto tile. Holding everyone to 2G means the falls
# you miss are the ones by the smallest, frailest users, which is precisely
# backwards.
#
# So: free fall followed by any deceleration past this floor counts. The free
# fall is what makes it a fall; the peak only says how hard.
IMPACT_MIN_ABS = 14.0

# Breathing band. 0.18-0.34 Hz is roughly 11-20 breaths a minute.
# The wide band is just the denominator for the power ratio.
RESP_BAND = (0.18, 0.34)
RESP_WIDE_BAND = (0.05, 3.0)
RESP_RATIO_MIN = 0.14

# Postural shifts.
# Started with 2.0s windows and it missed most of the small adjustments
# someone makes in a chair - short movements got averaged away inside the long
# window. 0.5s catches them.
SHIFT_WINDOW_S = 0.5
SHIFT_STD_MIN = 0.04
SHIFT_MIN_COUNT = 1

# v1 declared INACTIVITY_MINUTES = 30 and then never used it, while the code
# actually looked at 60 seconds. So the README, the design doc and the code
# each claimed a different number. 20 min is where false alarms hit zero in
# testing, so that's what this is.
INACTIVITY_WINDOW_S = 1200.0
PRODUCTION_INACTIVITY_S = 1800.0  # what we'd probably ship with

ACTIVE_STD_MIN = 0.12


def respiration_ratio(magnitude, fs=SAMPLING_RATE):
    """How much of the signal's power sits in the breathing band.

    Someone lying completely still is still breathing, and that shows up as a
    slow wobble around 0.25 Hz. A dropped device just gives sensor noise,
    which spreads power evenly and produces no peak.

    Returns 0-1. Higher means a clear peak in the breathing band.
    """
    sig = np.asarray(magnitude, dtype=float)

    # Need a few cycles of a 0.25 Hz signal before the FFT can resolve it.
    if sig.size < 4 * fs:
        return 0.0

    sig = sig - sig.mean()  # drop the ~9.81 gravity offset

    # Hann window, otherwise the abrupt ends of the recording smear energy
    # across the spectrum and swamp the band we care about.
    spectrum = np.abs(np.fft.rfft(sig * np.hanning(sig.size))) ** 2
    freqs = np.fft.rfftfreq(sig.size, d=1.0 / fs)

    band = (freqs >= RESP_BAND[0]) & (freqs <= RESP_BAND[1])
    wide = (freqs >= RESP_WIDE_BAND[0]) & (freqs <= RESP_WIDE_BAND[1])

    total = spectrum[wide].sum()
    if total <= 0:
        return 0.0

    return float(spectrum[band].sum() / total)


def count_postural_shifts(magnitude, fs=SAMPLING_RATE):
    """Count separate bursts of movement.

    Someone asleep turns over now and then. Someone unconscious doesn't.
    That difference is the whole point of this function.

    Counts runs of active windows rather than individual windows, so one long
    movement isn't counted as five shifts.
    """
    sig = np.asarray(magnitude, dtype=float)
    w = int(SHIFT_WINDOW_S * fs)

    if w < 1 or sig.size < w:
        return 0

    active = [sig[i * w:(i + 1) * w].std() > SHIFT_STD_MIN
              for i in range(sig.size // w)]

    shifts = 0
    prev = False
    for a in active:
        if a and not prev:
            shifts += 1
        prev = a

    return shifts


def find_impact(magnitude, fs=SAMPLING_RATE):
    """Find a fall: free fall followed by a hard landing.

    Returns the sample index of the impact, or None.

    Works forwards from the free fall rather than backwards from the largest
    peak. v1 of this function took argmax first and gave up if it wasn't above
    19.62, which threw away any fall that landed softly - and it also could
    only ever see one fall per session.
    """
    sig = np.asarray(magnitude, dtype=float)
    search = int(IMPACT_SEARCH_S * fs)

    below = np.flatnonzero(sig < FREE_FALL_THRESHOLD)
    if below.size == 0:
        return None

    # Group consecutive samples into distinct free-fall episodes.
    breaks = np.flatnonzero(np.diff(below) > 1)
    episodes = np.split(below, breaks + 1)

    for ep in episodes:
        end = int(ep[-1])
        after = sig[end:end + search]
        if after.size == 0:
            continue

        peak = int(np.argmax(after))
        if after[peak] >= IMPACT_MIN_ABS:
            return end + peak

    return None


def detect_alert(df, fs=SAMPLING_RATE, return_features=False):
    """Decide whether anyone needs contacting.

    Returns (alert, level, message). Pass return_features=True to also get the
    intermediate numbers, which is what you want when working out why it got
    something wrong.
    """
    mag = df["magnitude"].to_numpy(dtype=float)

    impact = find_impact(mag, fs)
    features = {"impact": impact is not None}

    # Something hit the ground. A person, or just the device?
    if impact is not None:
        resp = respiration_ratio(mag[impact:], fs)
        features["post_impact_resp_ratio"] = round(resp, 4)

        if resp >= RESP_RATIO_MIN:
            out = (True, "fall",
                   "MAJOR ALERT: fall detected, breathing present after "
                   "impact. Contacting family and emergency services.")
        else:
            # Nothing breathing means nothing is wearing it. Calling an
            # ambulance because a wristband fell off a shelf is exactly what
            # gets these systems unplugged.
            out = (False, "device_lost",
                   "No alert: impact but no breathing afterwards. Device "
                   "probably came off. Flagged for a check.")

        return (*out, features) if return_features else out

    # No impact. Are they moving?
    std = float(mag.std())
    features["overall_std"] = round(std, 4)

    if std > ACTIVE_STD_MIN:
        out = (False, "none", "No alert: normal activity.")
        return (*out, features) if return_features else out

    # They're still. Now the hard bit - asleep, or collapsed?
    resp = respiration_ratio(mag, fs)
    shifts = count_postural_shifts(mag, fs)
    duration = mag.size / fs

    features["resp_ratio"] = round(resp, 4)
    features["postural_shifts"] = shifts
    features["window_covered"] = duration >= INACTIVITY_WINDOW_S

    if resp < RESP_RATIO_MIN:
        # Not moving and not breathing - it's sitting on a table somewhere.
        out = (False, "device_lost",
               "No alert: no movement and no breathing. Device may not be worn.")

    elif shifts >= SHIFT_MIN_COUNT:
        out = (False, "none",
               f"No alert: at rest but still shifting position "
               f"({shifts} movements). Looks like sleep or sitting.")

    elif duration < INACTIVITY_WINDOW_S:
        # Haven't watched long enough to be sure. Three minutes of stillness
        # is normal, twenty isn't.
        out = (False, "none",
               f"No alert yet: still, but the {INACTIVITY_WINDOW_S:.0f}s "
               f"window isn't up. Keep watching.")

    else:
        out = (True, "inactivity",
               f"ALERT: breathing but no movement at all for {duration:.0f}s. "
               f"Person may be unable to move. Contacting family.")

    return (*out, features) if return_features else out