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

    elif state == "inactive":
        # Prolonged inactivity - person still, no meaningful movement
        # Magnitude stays close to 9.81 m/s2 with minimal variation
        # Standard deviation below 0.08 m/s2 indicates no activity
        x = np.random.normal(0, 0.04, n_samples)
        y = np.random.normal(0, 0.04, n_samples)
        z = np.ones(n_samples) * GRAVITY + np.random.normal(0, 0.03, n_samples)

    elif state == "fall":
        # Fall event - two phase pattern based on Bourke et al. (2007)
        # Phase 1: free fall - magnitude drops below 5.89 m/s2 (~200ms)
        # Phase 2: impact - magnitude spikes above 19.62 m/s2 (~100ms)
        # Phase 3: post fall stillness - person on ground, not moving

        # Start with normal activity
        x = 0.8 * np.sin(2 * np.pi * 1.8 * t) + np.random.normal(0, 0.4, n_samples)
        y = 0.6 * np.sin(2 * np.pi * 1.2 * t) + np.random.normal(0, 0.3, n_samples)
        z = GRAVITY + np.random.normal(0, 0.3, n_samples)

        # Fall occurs at 15 seconds
        fall_start = int(15 * fs)

        # Phase 1: free fall lasts approximately 200ms
        free_fall_samples = int(0.2 * fs)
        x[fall_start:fall_start + free_fall_samples] = np.random.normal(0, 1.5, free_fall_samples)
        y[fall_start:fall_start + free_fall_samples] = np.random.normal(0, 1.5, free_fall_samples)
        z[fall_start:fall_start + free_fall_samples] = np.random.normal(2.0, 1.0, free_fall_samples)

        # Phase 2: impact lasts approximately 100ms
        impact_start = fall_start + free_fall_samples
        impact_samples = int(0.1 * fs)
        x[impact_start:impact_start + impact_samples] = np.random.normal(12.0, 2.0, impact_samples)
        y[impact_start:impact_start + impact_samples] = np.random.normal(8.0, 2.0, impact_samples)
        z[impact_start:impact_start + impact_samples] = np.random.normal(15.0, 2.0, impact_samples)

        # Phase 3: complete stillness after impact
        still_start = impact_start + impact_samples
        x[still_start:] = np.random.normal(0, 0.03, n_samples - still_start)
        y[still_start:] = np.random.normal(0, 0.03, n_samples - still_start)
        z[still_start:] = np.ones(n_samples - still_start) * GRAVITY + np.random.normal(0, 0.03, n_samples - still_start)

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
    """
    Analyse movement data and determine alert level.

    Uses research-based thresholds:
    - Fall detection: free fall phase below 5.89 m/s2 followed by
      impact above 19.62 m/s2 (Bourke et al. 2007)
    - Inactivity: magnitude standard deviation below 0.08 m/s2
      sustained across the full recording window

    Returns:
        alert_level : 'none', 'inactivity', or 'fall'
        message     : description of what was detected
    """

    magnitude = df['magnitude']

    # Check for fall pattern - impact spike above threshold
    if magnitude.max() > IMPACT_THRESHOLD:
        impact_index = magnitude.idxmax()
        pre_impact = magnitude.iloc[max(0, impact_index - 15):impact_index]
        if pre_impact.min() < FREE_FALL_THRESHOLD:
            return 'fall', ('MAJOR ALERT: Fall detected — free fall and impact confirmed. '
                          'Alerting family and NHS immediately.')
        else:
            return 'fall', ('ALERT: High impact detected. '
                          'Alerting family — NHS contacted if no response.')

    # Check for prolonged inactivity
    if magnitude.std() < 0.08:
        return 'inactivity', ('ALERT: No movement detected for extended period. '
                             'Alerting family to check on user.')

    return 'none', 'Status: Normal activity detected. No alert required.'

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("AI Care Alert - Movement Simulation")
    print("Based on tri-axial accelerometer research")
    print("-" * 50)

    os.makedirs("data/simulated", exist_ok=True)

    for state in ["normal", "inactive", "fall"]:
        print(f"\nSimulating: {state} state")
        df = simulate_movement(state=state)
        alert_level, message = detect_alert(df)
        print(f"  Mean magnitude : {df['magnitude'].mean():.4f} m/s2")
        print(f"  Max magnitude  : {df['magnitude'].max():.4f} m/s2")
        print(f"  Std deviation  : {df['magnitude'].std():.4f} m/s2")
        print(f"  {message}")
        df.to_csv(f"data/simulated/{state}_movement.csv", index=False)

    print("\nSimulation complete.")
    print("Data saved to data/simulated/")