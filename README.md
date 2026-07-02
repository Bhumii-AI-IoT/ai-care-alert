# AI Care Alert

## The Problem

Some people face a silent risk every single day.

A fall. A sudden health episode. A moment where they need help 
but cannot reach anyone. This is the reality for elderly people, 
disabled individuals, those managing serious long term conditions, 
and people who live alone — a significant and growing part of 
our population.

Current solutions exist but they have real gaps. Most require the 
person to press a button — which assumes they are conscious, alert, 
and able to react in that moment. Many connect to paid monitoring 
centres rather than the people who actually care about them. And 
almost none are intelligent enough to detect an emergency when 
the person cannot signal one themselves.

This project explores a different approach — a system that combines 
a manual alert option with automatic AI-based movement monitoring, 
so that help can be triggered whether or not the person is able 
to ask for it.

For the elderly. For the disabled. For those managing serious illness. 
For anyone who deserves to feel safe — and whose family deserves 
peace of mind.

---

## How It Works

The system has two ways of detecting that someone needs help:

**Manual Alert**
- A wearable button the person can press themselves
- A mobile app with a single tap emergency alert

**Automatic AI Monitoring**
- Tri-axial accelerometer sensors monitor movement continuously
- Detects prolonged inactivity — no movement for an extended period
- Detects fall events — using free fall and impact phase patterns
  based on published research thresholds

---

## Alert System

| Situation | Who Gets Alerted |
|-----------|-----------------|
| Button pressed or inactivity detected | Family first |
| Fall confirmed or no response | Family and NHS simultaneously |

---

## Technical Approach

Movement detection is based on tri-axial accelerometer research:

- **Fall detection** uses a two-phase threshold approach — free fall 
  phase below 5.89 m/s² followed by impact above 19.62 m/s²
  (Bourke et al. 2007)
- **Inactivity detection** triggers when magnitude standard deviation 
  falls below 0.08 m/s² for a sustained period
- **Sampling rate** of 50Hz — standard for wearable accelerometers

---

## Repository Structure

| File | What It Contains |
|------|-----------------|
| docs/system_design.md | Full system design and alert logic |
| src/simulate_movement.py | Movement simulation and alert detection |
| data/simulated/ | Simulated sensor data for three states |

---

## Current Status

Research and concept design complete. Movement simulation with 
tiered alert detection is working. Next phase is expanding the 
simulation and exploring machine learning approaches for improved 
detection accuracy.

---

## Disclaimer

This is a research and concept project. It is not a certified 
medical device and is not intended for clinical use.