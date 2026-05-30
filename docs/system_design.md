# System Design

## AI Care Alert — Technical Overview

---

## 1. The Core Idea

Most emergency alert systems are reactive — they wait for a person 
to press a button. This system adds a second layer: AI-based movement 
monitoring that can detect an emergency even when the person cannot 
signal one themselves.

The two layers work together:
- Manual alert — for when the person can ask for help
- Automatic detection — for when they cannot

---

## 2. System Components

### 2.1 Input Methods

| Component | Type | Who Uses It |
|-----------|------|-------------|
| Wearable button | Physical device | Bed-bound or low mobility users |
| Mobile app | Smartphone | Users who can move independently |
| Movement sensor | Automatic | All users — no action needed |

### 2.2 AI Monitoring Layer

The movement sensor continuously tracks activity patterns.
The AI layer looks for two things:

- **Inactivity** — no movement detected for an unusually long period
- **Sudden fall** — rapid unexpected movement followed by no movement

When either pattern is detected, the system triggers an alert 
automatically — without requiring any input from the user.

### 2.3 False Alert Reduction

A known problem with alert systems is false alarms — accidental 
button presses or normal periods of stillness being misread as 
emergencies.

This system addresses that by cross-referencing the manual alert 
with movement data:
- If a button is pressed but movement data shows normal activity,
  the system flags it as a possible false alarm before escalating
- Automatic alerts only trigger after a defined inactivity threshold
  is crossed — not immediately

---

## 3. Alert Logic

The system uses a tiered approach to decide who gets notified:

| Trigger | First Alert | Second Alert |
|---------|-------------|--------------|
| Button pressed | Family / loved ones | NHS if no response |
| No movement for long period | Family / loved ones | NHS if no response |
| Major emergency confirmed | Family / loved ones | NHS simultaneously |

This ensures:
- Family is always the first contact
- NHS is only contacted when genuinely necessary
- No unnecessary burden on emergency services

---

## 4. User Types

The system is designed for three types of users:

**Type 1 — Low mobility users**
Cannot move independently. Primary alert method is the wearable 
button next to their bed. Automatic monitoring provides a safety 
net if they cannot reach the button.

**Type 2 — Mobile users**
Can move around but may need help quickly. Uses the mobile app 
for manual alerts. Automatic monitoring runs in the background.

**Type 3 — Independent users with health conditions**
Managing serious illness or disability. May not always recognise 
when they need help. Automatic monitoring is particularly important 
for this group.

---

## 5. What This System Does Not Do

- It does not replace professional medical care
- It does not diagnose medical conditions
- It does not store personal data beyond what is needed to function
- It is not a substitute for regular check-ins from family or carers

---

## 6. Current Development Status

This document describes the intended system design concept. 
This project is currently at the research and ideation stage — 
the system design, alert logic, and prototype code are being 
documented and developed. No physical hardware exists yet.

The code in this repository simulates how the system would 
behave — demonstrating the concept before any hardware 
is built.

## 7. Data Requirements for Future Development

When development moves beyond simulation, the following data 
will be needed:

- **Movement data** — accelerometer readings from real users
  in different scenarios (normal activity, falls, prolonged 
  inactivity)
- **Response time data** — how quickly alerts need to be sent
  to be genuinely useful in an emergency
- **False alarm patterns** — understanding what normal inactivity
  looks like (sleep, rest) vs genuine emergencies

This data would ideally come from research institutions, NHS 
datasets, or controlled studies with volunteer participants. 
Any real data collection would require full ethics approval 
and informed consent.