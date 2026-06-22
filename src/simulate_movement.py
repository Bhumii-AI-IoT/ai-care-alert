# simulate_movement.py
# Author: Bhumii-AI-IoT
# Project: AI Care Alert
# Description: Simulates tri-axial accelerometer data for detecting
#              movement states in vulnerable individuals.
#
# Research basis:
# - Bourke et al. (2007) - threshold-based tri-axial accelerometer
#   fall detection algorithm
# - Fall impact threshold: 19.62 m/s2 (2G)
# - Free fall threshold: 5.89 m/s2 (0.6G)
# - Sampling rate: 50Hz standard for wearable accelerometers

import numpy as np
import pandas as pd
import os

# ── Research-Based Constants ──────────────────────────────────────────────────

SAMPLING_RATE       = 50      # Hz - standard wearable accelerometer rate
DURATION            = 60      # seconds per session
GRAVITY             = 9.81    # m/s2 - standard gravity

# Thresholds from Bourke et al. (2007) fall detection research
FREE_FALL_THRESHOLD = 5.89    # m/s2 - free fall phase indicator
IMPACT_THRESHOLD    = 19.62   # m/s2 - ground impact indicator

# Inactivity alert threshold
INACTIVITY_MINUTES  = 30      # minutes before family alert triggers

RANDOM_SEED         = 42
np.random.seed(RANDOM_SEED)


# ── Movement Simulation ───────────────────────────────────────────────────────

def simulate_movement(duration=DURATION, fs=SAMPLING_RATE, state="normal"):
    """
    Simulate tri-axial accelerometer readings.
    Normal activity based on ADL research - magnitude varies
    between 8.5 and 12.5 m/s2 during typical daily movement.
    """

    n_samples = duration * fs
    t = np.linspace(0, duration, n_samples)

    if state == "normal":
        # Normal daily activity - walking, shifting position
        # Frequency of 1.8 Hz reflects average walking cadence
        x = 0.8 * np.sin(2 * np.pi * 1.8 * t) + np.random.normal(0, 0.4, n_samples)
        y = 0.6 * np.sin(2 * np.pi * 1.2 * t) + np.random.normal(0, 0.3, n_samples)
        z = GRAVITY + 0.5 * np.sin(2 * np.pi * 0.9 * t) + np.random.normal(0, 0.3, n_samples)
    else:
        # Other states to be added
        x = np.zeros(n_samples)
        y = np.zeros(n_samples)
        z = np.ones(n_samples) * GRAVITY

    magnitude = np.sqrt(x**2 + y**2 + z**2)

    df = pd.DataFrame({
        "time_s"    : t,
        "accel_x"   : x,
        "accel_y"   : y,
        "accel_z"   : z,
        "magnitude" : magnitude
    })

    return df


# ── Alert Detection ───────────────────────────────────────────────────────────

def detect_alert(df):
    # To be implemented
    pass


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("AI Care Alert - Movement Simulation")
    print("Development in progress.")