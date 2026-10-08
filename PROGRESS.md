# Progress

**Current phase:** 2-3 (environment, baselines, agents)  
**Last update:** 2026-10-09

| Phase | Status | Notes |
| --- | --- | --- |
| 0 Setup and toy junction | done | Python 3.11.16, SUMO 1.28.0, toy runs under TraCI and libsumo |
| 1 Network and demand | done | Plain-XML junction, 4 regimes, 200-file DR pool, Webster plans |
| 2 Env, rewards, baselines, budget | in progress | 23 tests green; baselines evaluating |
| 3 Agents and sanity checks | in progress | Double DQN, SB3 DQN, PPO implemented |
| 4 Training queue | pending | |
| 5 Website | pending | |
| 6 Evaluation, figures, replays, export | pending | |
| 7 Local demo and report | pending | |
| 8 Polish, GitHub, Vercel | pending | |

## Key numbers

- Peak demand: 3,636 veh/h, Webster cycle 120 s, design degree of saturation 0.85.
- No teleports in any baseline probe run.

## Open issues

- None blocking.

## Training queue

<!-- queue:start -->
Profile `day` - updated 2026-10-09 01:31 - 2 done, 7 running

| Job | State | Steps | Minutes | Best validation score |
| --- | --- | --- | --- | --- |
| sweep_l0.25_T120__s0 | running | 30000 |  |  |
| sweep_l0.25_T60__s0 | running | 30000 |  |  |
| sweep_l0.25_T90__s0 | running | 30000 |  |  |
| sweep_l1_T120__s0 | running | 30000 |  |  |
| sweep_l1_T60__s0 | done | 30000 | 20.0 | -0.0626 |
| sweep_l1_T90__s0 | running | 30000 |  |  |
| sweep_l4_T120__s0 | done | 30000 | 22.9 | -0.0182 |
| sweep_l4_T60__s0 | running | 30000 |  |  |
| sweep_l4_T90__s0 | running | 30000 |  |  |
<!-- queue:end -->
