# GreenWave-RL: slide outline (12 slides, 8-minute demo)

_Numbers filled by `report/fill.py`._

1. **Title.** GreenWave-RL: fairness-aware deep RL for signal control under mixed Indian traffic.
2. **The problem.** Plans go stale; traffic is mixed; a bus is not a car; averages can starve a minor road.
3. **The junction.** Generic 4-arm junction (plain XML). Left-hand traffic, four classes, split phasing. Demand is **synthetic**: no vehicles were counted at a real junction. _(Demo: /junction, 1 min)_
4. **The decision process.** State, action, constraints in the environment, truncation not termination.
5. **The reward.** Passenger weights and the fairness penalty; lambda = 4, T = 90 s from a sweep.
6. **Agents and baselines.** Double DQN from scratch; SB3 DQN and PPO; Webster, actuated, max-pressure, random.
7. **Fixed-time vs RL.** _(Demo: scene Hero, 2 min.)_ Peak wait per person: 21.3 s vs 34.2 s.
8. **The surge.** _(Demo: scene Surge, 1 min.)_ 14.9 s vs 36.4 s per person.
9. **The starvation problem.** _(Demo: scene Starvation, 2 min.)_ 115 s against 174 s, skewed regime, budget-matched runs; p = 0.029, significant.
10. **The bus.** _(Demo: scene Bus, 1 min.)_ 29.3 s against 37.8 s, peak regime, budget-matched runs; p = 0.17, not statistically significant.
11. **Results and the honest finding.** _(Demo: /results and scene Honest, 1 min.)_ Against a fixed-time plan tuned for each demand pattern, the regime-matched Double DQN cuts wait per person significantly in 3 of 4 regimes (low, peak, surge). Against max-pressure, a rule that needs no training, it is significantly better on wait per person in no regime, significantly worse in no regime, and statistically tied in low, peak, skewed, surge. On the maximum wait it is better in no regime, worse in no regime and tied in low, peak, skewed, surge. Significance is a Welch t-test over 10 held-out seeds at p < 0.05.
12. **Limits and next steps.** Sim-to-real gap, perfect observations, one junction; corridor control next.

Backups if SUMO GUI lags on the projector: the website served offline (`npx serve web/out`) and `docs/demo.gif`.
