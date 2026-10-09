# Viva notes

_Answers use this project's own results; numbers filled by `report/fill.py`._

## Write these from memory

Q-learning update:

```
Q(s, a) <- Q(s, a) + alpha * [ r + gamma * max_a' Q(s', a') - Q(s, a) ]
```

One Double DQN training step:

```
a = argmax Q(s) with probability 1 - epsilon, else random
s', r, terminated, truncated = env.step(a)
buffer.add(s, a, r, s', terminated)
batch = buffer.sample(64)
a* = argmax_a' Q_online(s'_b, a')
y  = r_b + gamma * (1 - terminated_b) * Q_target(s'_b, a*)
loss = Huber(Q_online(s_b, a_b), y); backprop; clip gradient norm at 10; Adam step
update the target network from the online network
```

## Likely questions

**Is your state Markov?** No, strictly. It omits upstream arrivals and vehicles between observations, so the agent
acts under partial observability. It works because queues, densities and longest waits summarise most of what
decides the next few seconds.

**Why a target network and a replay buffer?** Bootstrapped targets move with every update and consecutive samples are
correlated; both destabilise Q-learning with function approximation. A slowly changing target and shuffled replay fix
the two problems separately.

**Why does DQN overestimate, and what does Double DQN change?** The max over noisy estimates is biased upward. Double
DQN lets the online network pick the action and the target network evaluate it.

**Why is your reward not simply negative waiting time?** The difference form credits the change an action caused and
is denser. Its discounted return is equivalent to minimising accumulated waiting on the approaches, which is also why
checkpoints are selected with that potential form: the undiscounted sum of differences telescopes to the final state.

**Why can max-pressure match your agent?** It is throughput-optimal under idealised assumptions and needs no training.
Our numbers: Against a fixed-time plan tuned for each demand pattern, the regime-matched Double DQN cuts wait per person significantly in 3 of 4 regimes (low, peak, surge). Against max-pressure, a rule that needs no training, it is significantly better on wait per person in no regime, significantly worse in no regime, and statistically tied in low, peak, skewed, surge. On the maximum wait it is better in no regime, worse in no regime and tied in low, peak, skewed, surge. Significance is a Welch t-test over 10 held-out seeds at p < 0.05.

**Would this work on the real junction?** Not as it stands. Sim-to-real gap: sensing errors, driver behaviour,
pedestrians, safety certification. Demand is **synthetic**: no vehicles were counted at a real junction.

**How do you know the agent has converged?** By the validation score on held-out seeds across 3
training seeds flattening out, not by one training curve. See the learning-curve figure and its seed bands.

**Why are safety constraints in the env, not the reward?** A constraint is a guarantee; a penalty is a price the agent
may choose to pay. `tests/test_safety.py` checks 100 random-policy episodes against the signal states SUMO applied.

**Why is episode end truncation, not termination?** Traffic does not stop at 3600 s.
Treating the limit as terminal would bias values near the end, so the target bootstraps from the last state.

**Your transitions last 5 s or 13 s. Is constant gamma correct?** It is a semi-MDP simplification. The
`--smdp-discount` flag uses gamma^(dt/5) to test it.

**Why passenger weights of 40 for a bus?** A stated occupancy assumption. The ablation
runs bus weights of 20, 40 and 60: Bus delay by assumed occupancy (bus = 20: 32.7 s, bus = 40: 29.3 s, bus = 60: 31.9 s). Wait per person varies by 2.5 s across the three weights.

**Does the fairness penalty do anything?** Without the penalty the maximum wait goes from 115 s to 174 s (+51%, p = 0.029, significant) and wait per person from 15.7 s to 12.9 s (p = 0.046, significant).

**Why only one junction?** Scope. Corridor multi-agent control is the first extension.
