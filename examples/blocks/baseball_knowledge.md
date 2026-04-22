---
name: baseball_knowledge
description: Domain knowledge about batted-ball analytics (exit velocity, launch angle, xAvg).
load: when
when: "\\b(baseball|exit velo(city)?|launch angle|xavg|batted ball|pitcher|hitter)\\b"
---
Context for batted-ball questions:

- **Exit velocity** is the speed of the ball off the bat (mph). Typical D1 average is ~85 mph; elite is 95+.
- **Launch angle** is the vertical angle of the batted ball (degrees). The "sweet spot" window is ~10–30° for line drives.
- **xAvg** (expected batting average) predicts hit probability given exit velocity + launch angle, based on
  historical outcomes of similar batted balls. A ball with high xAvg that ended in an out is sometimes called
  "robbed" — the hitter did everything right but got unlucky.

When a user describes a specific batted ball, cross-reference these ranges before answering.
