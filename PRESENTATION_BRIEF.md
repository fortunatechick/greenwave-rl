# GreenWave-RL: Complete Project Brief for Building the Presentation

> **How to use this file.** This is a self-contained brief about one finished college project. Give it to an AI
> assistant (or a person) who will build the slide deck. It follows the 14-section structure the college requires,
> in order. Every number here comes from the project's own evaluation files; none is invented or rounded in a
> favourable direction. Section 15 lists the figures that already exist, Section 16 gives viva questions with
> answers, and Section 17 lists what must **not** be claimed.

---

## 0. Instructions for whoever builds the deck

- Required order of sections: 1 Abstract, 2 Introduction, 3 Objectives, 4 Scope, 5 Literature Survey, 6 Proposed
  System, 7 Methodology, 8 Dataset, 9 Software & Hardware Requirement, 10 Results and Discussion, 11 Observation
  and Finding, 12 Conclusion, 13 Future Scope, 14 References.
- Suggested length: 22-28 slides. Results and Methodology deserve the most slides (4-6 each).
- Keep it honest. The headline result is **not** "RL beats everything". It is: RL clearly beats fixed-time
  signals, statistically ties a strong classical rule (max-pressure), and the fairness penalty measurably protects
  the worst-off drivers. Section 17 lists claims to avoid.
- Tone: academic but plain. Use numbers with units (seconds, vehicles per hour). Show mean ± standard deviation
  where space allows.
- Suggested visual theme (matches the project website): dark "traffic control room" look, near-black background
  (#0A0C0F), green (#3DDC84) and teal (#2BD4C8) accent for "ours", red (#FF4D4F) only for "worse", amber (#FFB020)
  for warnings. Vehicle colours: two-wheeler light blue, auto-rickshaw yellow, car grey, bus lavender.
- Course context: Artificial Intelligence, B.Tech Computer Engineering, 3rd year.

---

## 1. Abstract

Fixed-time traffic signals run the same timing plan regardless of how traffic changes minute to minute. This
project builds a microscopic traffic simulation of a four-way signalised junction with **mixed Indian traffic**
(two-wheelers, auto-rickshaws, cars and buses, with two-wheelers filtering between lanes) and trains **deep
reinforcement learning (RL)** agents to choose which approach gets the green light, every 5 seconds, from live
queue observations.

The main agent is a **Double Deep Q-Network (Double DQN) written from scratch in PyTorch**. It is compared with two
library agents (DQN and PPO from Stable-Baselines3) and four classical controllers (Webster fixed-time,
SUMO actuated control, max-pressure, and random) across **four demand patterns**: low, peak, skewed (one road much
busier) and surge (a 10-minute burst on one road).

The original contribution is the **reward design**: waiting time is weighted by **how many people each vehicle
carries** (a bus counts far more than a car), and a **fairness penalty** punishes the controller whenever any road's
longest-waiting vehicle exceeds a threshold, so the agent cannot "starve" a quiet side road. The project also
measures **generalisation**: how a policy trained on one traffic pattern performs on the others, and how much
**domain randomisation** (training on randomly varied demand) helps.

**Key results (10 unseen test runs per pattern):**
- Against a fixed-time plan tuned for each pattern, the RL agent cuts average waiting per person significantly in
  3 of 4 patterns; in the surge pattern from **36.4 s to 14.9 s (−59%)**.
- Against max-pressure, a strong classical rule that needs no training, the agent is **statistically tied** in all
  four patterns.
- The fairness penalty lowers the longest wait from **174 s to 115 s (−34%, p = 0.029)**, at a cost of a slightly
  higher average wait (12.9 s → 15.7 s per person).
- Domain randomisation recovers **55%** of the performance lost when a policy meets traffic it was not trained on.

---

## 2. Introduction

### 2.1 The problem in everyday terms
- Most signals in Indian cities run **fixed cycles**: each road gets a set number of seconds of green, in a fixed
  order, whether or not cars are waiting.
- Timing plans are tuned by hand for an "average hour" and go stale as traffic changes through the day.
- Indian traffic is **mixed and weakly lane-disciplined**: two-wheelers squeeze between cars, autos and buses share
  lanes. Much published research on AI traffic signals assumes neat queues of identical cars.
- A bus carrying 40 people and a car carrying 2 people are both "one vehicle" to a normal controller. That
  undervalues public transport.
- A controller that only minimises *average* delay can learn to keep a quiet side road on red for a very long time,
  because few vehicles wait there. A real controller must not do that.

### 2.2 Why reinforcement learning?
- Signal control is a **sequential decision problem**: every few seconds the controller decides, and each decision
  affects future queues. RL is designed exactly for learning such decision policies by trial and error.
- An RL agent learns from simulated experience; no labelled "correct" timings are needed.

### 2.3 Problem statement (one sentence for the slide)
> Given a signalised junction with time-varying, mixed traffic, learn a phase-selection policy that minimises delay
> **per person**, keeps the **worst-case wait bounded**, and stays effective when demand **shifts** away from what it
> was trained on.

### 2.4 Key terms (for a glossary slide if needed)
| Term | Meaning |
| --- | --- |
| Phase | Which approach (road) currently has green. Here: 4 phases, one per road (N, E, S, W). |
| Split phasing | Each road gets its own green for all its movements (left, straight, right), common in India. |
| Free left turn | Left-turning vehicles may go even on red after yielding (left-hand traffic). |
| Reinforcement learning | An agent learns by acting, receiving a reward, and improving its policy. |
| Q-value | The expected future reward of taking an action in a state. |
| DQN / Double DQN | Neural networks that estimate Q-values; Double DQN reduces over-estimation. |
| PPO | A policy-gradient RL algorithm (learns the policy directly). |
| Max-pressure | Classical rule: give green to the road whose queue minus downstream queue is largest. |
| PCU | Passenger Car Unit: a bus takes the road space of 2.2 cars, a two-wheeler 0.5. |
| SUMO | Simulation of Urban MObility, an open-source microscopic traffic simulator. |
| Domain randomisation | Training on many randomly varied traffic patterns so the policy generalises. |

---

## 3. Objectives

1. Build a **SUMO simulation** of a four-arm junction with **four vehicle classes** and **sub-lane (lateral)
   movement**, in **left-hand traffic**.
2. Formulate signal control as a **Markov Decision Process (MDP)** and implement it as a standard **Gymnasium
   environment**, with safety rules (minimum green, yellow, maximum green) **enforced by the environment, not
   learned**.
3. Implement **Double DQN from scratch** in PyTorch, and train **DQN and PPO** (Stable-Baselines3) for comparison.
4. Implement **four classical baselines**: Webster fixed-time, actuated, max-pressure, random.
5. Design and test a **passenger-weighted, fairness-aware reward**.
6. Measure **generalisation** across four demand patterns and the effect of **domain randomisation**.
7. Run **ablation studies** to show what each design choice contributes.
8. Deliver a **demo**: a side-by-side live SUMO view and a website that replays recorded simulations.

---

## 4. Scope

### In scope
- One isolated, signalised **four-way junction**: major road east-west (3 lanes each way), minor road north-south
  (2 lanes each way), 250 m approaches, 3.5 m lanes, speed limit 50 km/h (13.89 m/s).
- Four vehicle classes with Indian-style mixed traffic and lane filtering.
- Four demand patterns (low, peak, skewed, surge) plus randomised demand for training.
- Comparison of 3 RL agents and 5 classical controllers on identical traffic.
- Evaluation on 10 held-out random seeds per pattern; statistical significance tests.
- A static website with replays and full results; a local side-by-side demo.

### Out of scope / limitations (state them on the slide)
- **No real-world deployment**: everything is in simulation.
- **Synthetic demand**: no vehicles were counted at a real junction; the junction is generic, not a named site.
- **Perfect sensing**: the agent reads exact queues from the simulator (a real system would use cameras or loops).
- **One junction**: no coordination between neighbouring signals (a corridor is future work).
- **No pedestrians** or emergency-vehicle priority.

---

## 5. Literature Survey

> Note: these references were listed from memory by the project; titles and years should be double-checked before
> final submission.

| # | Work | Key idea | How this project uses or differs from it |
| --- | --- | --- | --- |
| 1 | Sutton & Barto, *Reinforcement Learning: An Introduction* | MDPs, Q-learning, temporal-difference learning | Theoretical foundation for the MDP formulation |
| 2 | Mnih et al. (2015), *Human-level control through deep RL* (DQN) | Neural Q-function, experience replay, target network | DQN baseline (via Stable-Baselines3); replay and target net in our agent |
| 3 | van Hasselt et al. (2016), *Deep RL with Double Q-learning* | Separate action selection and evaluation to cut over-estimation | Our main agent is Double DQN, written from scratch |
| 4 | Schulman et al. (2017), *Proximal Policy Optimization* | Stable policy-gradient updates with clipping | PPO comparison agent |
| 5 | Varaiya (2013), *Max pressure control of a network of signalized intersections* | Throughput-optimal rule using queue differences | Strongest classical baseline in every table |
| 6 | Webster (1958) signal timing method | Optimal cycle length C₀ = (1.5L + 5)/(1 − Y) | Fixed-time baseline, tuned per demand pattern |
| 7 | Wei et al. (2018), *IntelliLight* | Deep RL for real-world traffic lights | Shows RL signal control is feasible; we add mixed traffic + fairness |
| 8 | Wei et al. (2019), *PressLight* | RL reward based on max-pressure | Our "pressure" reward ablation is inspired by it |
| 9 | Wei et al. (2019), *A Survey on Traffic Signal Control Methods* | Overview of classical and RL methods | Positioning of the project |
| 10 | Ault & Sharon (2021), *RL Benchmarks for Traffic Signal Control* | RL must be compared fairly against strong classical baselines | Motivates keeping max-pressure in every comparison |
| 11 | Lopez et al. (2018), *Microscopic Traffic Simulation using SUMO* | The SUMO simulator | Simulation platform |
| 12 | IRC:106-1990 (Indian Roads Congress) | PCU values for Indian mixed traffic | PCU factors used here |

**Research gap this project addresses:** most RL signal work (a) treats every vehicle equally, (b) assumes
lane-disciplined, car-only traffic, (c) optimises only average delay, which can starve minor roads, and (d) rarely
tests what happens when traffic differs from training. GreenWave-RL addresses all four.

---

## 6. Proposed System

### 6.1 System overview (8-stage pipeline, good for a block diagram)
1. **Network builder**: turns lane counts into a SUMO road network (left-hand traffic, 4 split phases).
2. **Demand generator**: creates random (Poisson) vehicle arrivals for 4 vehicle classes and 4 demand patterns,
   plus 200 randomised demand files for domain randomisation.
3. **SUMO simulator**: moves every vehicle second by second, including two-wheelers filtering between lanes.
4. **Gym environment**: wraps SUMO as an MDP; observes queues; applies the agent's choice; enforces safety timing.
5. **Agent**: Double DQN (ours), DQN, PPO.
6. **Baselines**: Webster fixed-time, actuated, max-pressure, random, through the same environment.
7. **Evaluator**: 10 unseen seeds per pattern, per-vehicle trip records, Welch t-tests.
8. **Demo**: website replays + live side-by-side SUMO windows.

### 6.2 What makes it different (three contributions)
1. **Reward design (original contribution):** passenger-weighted waiting time + maximum-wait fairness penalty.
2. **Realistic setting:** left-hand traffic, four mixed vehicle classes with sub-lane movement, free left turn,
   approach-wise split phasing as used at Indian junctions; not a toy grid.
3. **Honest generalisation study:** train on one pattern, test on all, report failures, measure what domain
   randomisation recovers; max-pressure kept in every comparison.

### 6.3 Safety by design
The agent can only choose *which road gets green next*. The environment guarantees:
- minimum green of **10 s**, a **3 s yellow** on every change, maximum green of **60 s**;
- if a green reaches 60 s, the environment **forces** a switch to the road with the longest wait.
These rules are verified by an automated test running 100 random-policy episodes against the signal states SUMO
actually applied.

### 6.4 Signal timing state machine (diagram)
```
GREEN(road p)  --agent picks p again-->  GREEN(p) for 5 more seconds
GREEN(road p)  --agent picks road q-->   YELLOW(p) 3 s --> GREEN(q) for at least 10 s
GREEN(p) reaches 60 s                    --> forced switch to the longest-waiting road
```

---

## 7. Methodology

### 7.1 MDP formulation
| Element | Definition |
| --- | --- |
| **State** (29 numbers) | For each of the 10 incoming lanes: queue (PCU of stopped vehicles ÷ lane capacity) and density (PCU on lane ÷ capacity). Plus: current green road (one-hot, 4), time since last change ÷ 60 s, and the longest current wait on each road ÷ T (4). |
| **Action** | Which of the 4 roads gets green next. Choosing the current road extends its green by 5 s. |
| **Decision interval** | Every 5 s (a switch takes 13 s: 3 s yellow + 10 s minimum green). |
| **Reward** | Passenger-weighted reduction in total waiting time, minus a fairness penalty (below). |
| **Episode** | 3,600 simulated seconds (1 hour). The end is treated as a time limit (truncation), not a terminal state. |
| **Discount γ** | 0.95 per decision (see 7.6 for why not 0.99). |

Lane capacity in PCU = lane length ÷ 7.5 m.

### 7.2 Reward function (the core contribution)
Baseline reward (common in the literature):

    r = (W_previous − W_now) / κ

Our reward:

    r = (1/κ) · Σ_classes  w_c · (W_c,previous − W_c,now)   −   λ · max(0, longest_wait_on_any_road − T) / T

- W_c = total accumulated waiting time of vehicles of class c on the incoming roads.
- w_c = passenger weight of class c: two-wheeler 1.5, car 2, auto-rickshaw 2.5, bus 40 (assumed average occupancy).
  In training these are divided by the traffic mix's average occupancy (4.525) so the reward has a sensible scale;
  their ratios stay the same (a bus counts 20× a car).
- κ = 100 (scale). **λ = 4** and **T = 90 s** were chosen by a 9-run sweep (7.5).
- The first term rewards the agent for clearing waiting people; the second punishes it whenever any road's
  longest-waiting vehicle exceeds 90 s.

### 7.3 Agents
**Double DQN (main agent, written from scratch in PyTorch)**
- Neural network: 29 inputs → 128 → 128 → 4 outputs (ReLU).
- Replay buffer 50,000 transitions; batch size 64; Adam optimiser, learning rate 1e-4.
- Target network copied every 500 steps; training starts after 2,000 steps.
- ε-greedy exploration from 1.0 down to 0.05 over the first half of training.
- Huber loss; gradient clipping at norm 10.
- Double DQN target: y = r + γ · Q_target(s′, argmax_a′ Q_online(s′, a′)), the online network *chooses* the next
  action and the target network *evaluates* it, which reduces over-estimation.
- Checkpoint selection on 2 held-out validation seeds.

Training step (good for a pseudocode slide):
```
a  = best action from Q-network with probability 1−ε, else random
s', r = environment.step(a)
store (s, a, r, s', done) in replay buffer
sample 64 transitions
a* = argmax over a' of Q_online(s')
y  = r + γ · Q_target(s', a*)        (no bootstrap only on true termination)
loss = Huber(Q_online(s, a), y); gradient step; clip gradients
every 500 steps: copy online network → target network
```

**DQN (Stable-Baselines3)**: vanilla DQN (not Double), same network and schedule.
**PPO (Stable-Baselines3)**: 4 parallel simulations, 512 steps per rollout, 10 epochs, clip 0.2, entropy 0.01.

### 7.4 Classical baselines
| Baseline | How it works |
| --- | --- |
| **Webster fixed-time (matched)** | Cycle C₀ = (1.5L + 5)/(1 − Y), greens split by each road's flow ratio. A separate plan is tuned for each demand pattern (the strongest fixed-time). |
| **Webster fixed-time (stale peak plan)** | The peak-hour plan used everywhere, the realistic "never re-tuned" case. |
| **Actuated** | SUMO's built-in gap-based control: extends green while cars keep arriving (10-60 s, 3 s gap). |
| **Max-pressure** | Gives green to the road with largest (incoming queue − outgoing queue). Needs no training. |
| **Random** | Random road each decision (sanity floor). |

Saturation flow for Webster: 525 PCU/h per metre of road width (IRC-style). Lost time per phase: 3 s yellow + 2 s
start-up.

### 7.5 Training procedure
1. **Budget planner** measured the simulator at ~55 decisions/s per process and chose the "day" profile (fits a
   one-day build): main runs 100,000 steps × 3 seeds; ablations 50,000 steps × 2 seeds.
2. **Toy sanity check**: on a simple one-lane junction, Double DQN reached a 52 s mean wait vs 131 s for random
   within 20,000 steps, which confirmed the agent learns before the real runs.
3. **λ/T sweep**: 9 short runs on the skewed pattern, λ ∈ {0.25, 1, 4} × T ∈ {60, 90, 120}. Rule: lowest wait per
   person among settings whose maximum wait ≤ 1.2·T. **Chosen: λ = 4, T = 90 s** (13.3 s per person, 74 s max wait).
4. **Main runs**: Double DQN on each of the 4 patterns + on randomised demand (3 seeds each); DQN and PPO on peak.
5. **Ablations**: 13 variants, each compared with a reference trained with the same budget.
6. In total **58 training jobs, 0 failed, 26.7 CPU-hours** on 7 parallel workers (about 4.5 hours of wall time).

### 7.6 A problem we found and fixed (good "engineering story" slide)
- With the textbook discount γ = 0.99, agents learned very quickly (better than max-pressure by 10,000 steps) and
  then **collapsed** (average queue jumped from ~12 to ~65 vehicles by 20,000 steps).
- We stopped training and ran **7 diagnostic variants** (lower learning rate, slower target updates, Polyak
  averaging, learning-rate decay, reward clipping, γ = 0.95, a combination).
- **γ = 0.95** stayed stable throughout; reward clipping to ±3 also helped. Both were adopted for all three agents.
- Reason: the waiting-time reward makes Q-values grow with congestion; a shorter horizon and clipped rewards keep
  them in a learnable range.
- This deviation from the original plan is documented, not hidden.

### 7.7 Evaluation protocol
- Policies frozen (no exploration). **10 evaluation seeds** (1000-1009) per pattern, never used in training.
- Every vehicle's trip is recorded; RL results average the 3 trained seeds per test seed.
- Reported: mean ± standard deviation over the 10 seeds; **Welch's t-test** against fixed-time and max-pressure
  (significant if p < 0.05).
- Seeds 900-901 select checkpoints; seeds 902-906 select λ and T, so test seeds stay untouched.

### 7.8 Metrics
| Metric | Definition |
| --- | --- |
| Wait per person (s) | Average time stopped, weighted by how many people each vehicle carries (**main metric**) |
| Wait per vehicle (s) | Plain average stopped time per vehicle |
| Max wait (s) | Longest any single vehicle waited (fairness) |
| Wait p95 (s) | 95th-percentile waiting time |
| Avg queue (veh) | Stopped vehicles on the approaches, averaged over every second |
| Throughput (veh/h) | Vehicles that completed their trip per hour |
| Delay by class (s) | Time lost per vehicle for each vehicle class |
| CO₂ (g/veh) | From SUMO's emission model |

---

## 8. Dataset

**There is no downloaded dataset.** All data is **generated** by simulation. This is normal for RL signal control:
the agent learns from experience in a simulator. State clearly that the demand is **synthetic**.

### 8.1 Road network
- Generic four-arm junction built from plain XML with SUMO's `netconvert`, left-hand traffic.
- Major road E-W: 3 lanes in, 3 out. Minor road N-S: 2 lanes in, 2 out. 250 m approaches, 3.5 m lanes.
- 18 signal links, 4 green phases (one per road), free left turn.

### 8.2 Vehicle classes (assumptions)
| Class | Share of traffic | Size (m) | Max speed | PCU | Passenger weight |
| --- | --- | --- | --- | --- | --- |
| Two-wheeler | 45% | 1.9 × 0.8 | 16 m/s | 0.5 | 1.5 |
| Car | 30% | 4.3 × 1.8 | 16 m/s | 1.0 | 2 |
| Auto-rickshaw | 18% | 2.6 × 1.4 | 12 m/s | 1.2 | 2.5 |
| Bus | 7% | 12.0 × 2.5 | 13 m/s | 2.2 | 40 |

Turn split on every road: 25% left, 55% straight, 20% right. Arrivals are random (Poisson).

### 8.3 Demand patterns
Peak volume was calibrated so the Webster plan runs at a degree of saturation of 0.85, with the major road carrying
1.5× the minor road.

| Pattern | Definition | Total vehicles/hour | Webster cycle (s) |
| --- | --- | --- | --- |
| Low | 0.4 × peak everywhere | 1,454 | 52 |
| Peak | 1.0 × peak | 3,636 | 120 |
| Skewed | East road 1.6 × peak, others 0.6 × peak | 3,272 | 88 |
| Surge | 0.7 × peak + 10-minute burst at 2.5 × on the east road (t = 1500-2100 s) | 2,872 | 78 |
| Randomised (training only) | 200 files, each road scaled by a random factor between 0.5 and 1.5 | varies | n/a |

Peak demand by class: 1,636 two-wheelers, 1,091 cars, 654 autos, 255 buses per hour.

### 8.4 How much data the agents saw
- Each main training run = 100,000 decisions (roughly 200-300 simulated hours of traffic).
- Total across all jobs ≈ 3.7 million decisions.
- Evaluation: 10 one-hour episodes per controller per pattern, roughly 1,400-3,600 vehicles each.

---

## 9. Software & Hardware Requirement

### 9.1 Software
| Component | Tool / version |
| --- | --- |
| Language | Python 3.11 |
| Traffic simulator | Eclipse SUMO 1.28.0 (installed via the `eclipse-sumo` pip package), libsumo / TraCI APIs |
| RL environment API | Gymnasium 1.4 |
| Deep learning | PyTorch 2.14 (CPU) |
| RL library | Stable-Baselines3 2.9 (DQN, PPO) |
| Analysis | NumPy, pandas, SciPy (Welch t-test), Matplotlib, seaborn |
| Logging | TensorBoard |
| Live demo dashboard | Streamlit |
| Testing / quality | pytest (30 tests), ruff (linting), GitHub Actions CI |
| Website | Next.js 16 (static export), React 19, TypeScript, Tailwind CSS 4, Motion, Recharts, KaTeX, Zustand, Zod |
| Hosting (planned) | Vercel (free static hosting) |
| Version control | Git + GitHub (private repository) |
| OS | Windows 11 (also runs on Linux and macOS) |

### 9.2 Hardware used
| Item | Specification |
| --- | --- |
| CPU | Intel Core i5-12450H, 8 cores / 12 threads |
| RAM | 16 GB |
| GPU | Not required (training is CPU-bound; simulation is the bottleneck) |
| Disk | < 1 GB for code, results and models |
| Training time | 26.7 CPU-hours on 7 parallel workers (~4.5 hours wall time) |

### 9.3 Minimum requirement to run the demo
Any modern laptop with Python 3.11 and a browser. The website runs in any browser with no server.

---

## 10. Results and Discussion

All numbers: mean over 10 unseen test seeds (± standard deviation where shown). "Ours" = Double DQN with the fair
reward, trained on the same pattern it is tested on, unless stated.

### 10.1 Main result: average wait per person (seconds, lower is better)
| Controller | Low | Peak | Skewed | Surge |
| --- | --- | --- | --- | --- |
| Fixed-time, stale peak plan | 29.9 | 34.2 | 68.0 | 50.7 |
| Fixed-time, plan tuned per pattern | 12.1 | 34.2 | 25.7 | 36.4 |
| Actuated (SUMO) | 12.4 | 23.0 | 18.0 | 20.8 |
| **Max-pressure** | **9.1** | **16.3** | 17.8 | 17.6 |
| Random | 28.6 | 60.9 | 106.3 | 66.2 |
| DQN (SB3, trained on peak) | 15.0 | 22.0 | 20.6 | 17.6 |
| PPO (SB3, trained on peak) | 12.1 | 21.7 | **14.5** | 17.3 |
| **Double DQN, fair (ours)** | 9.3 | 21.3 | 17.7 | **14.9** |
| Double DQN, fair + domain randomisation (ours) | 14.5 | 28.5 | 14.7 | 18.1 |

Standard deviations for "ours": low ±0.3, peak ±9.4, skewed ±6.8, surge ±2.1. For max-pressure: ±0.4, ±1.9, ±12.1,
±10.5.

**Statistical tests (ours vs ...):**
| Pattern | vs fixed-time (tuned): p-value | vs max-pressure: p-value |
| --- | --- | --- |
| Low | < 0.001 (significant, better) | 0.21 (tie) |
| Peak | 0.002 (significant, better) | 0.13 (tie) |
| Skewed | 0.079 (not significant) | 0.98 (tie) |
| Surge | 0.002 (significant, better) | 0.45 (tie) |

### 10.2 Other metrics (surge pattern, where RL looks best)
| Controller | Wait/vehicle (s) | Avg queue (veh) | Max wait (s) | Wait p95 (s) | CO₂ (g/veh) | Throughput (veh/h) |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed-time (tuned) | 35.2 | 27.7 | 231 | 126 | 187 | 2,795 |
| Actuated | 19.9 | 15.7 | 169 | 68 | 152 | 2,796 |
| Max-pressure | 18.3 | 14.2 | 162 | 71 | 152 | 2,800 |
| PPO | 17.1 | 13.4 | 135 | 62 | 149 | 2,798 |
| **Double DQN (ours)** | **15.7** | **12.3** | **122** | **51** | **146** | 2,796 |

Throughput is nearly identical for all controllers (the junction is not over capacity), so the differences are in
**waiting**, not in how many vehicles get through.

### 10.3 Learning curves
DQN, Double DQN and PPO all reach a validation score close to their best within the first 10,000-20,000 steps.
Double DQN's curve shows occasional sharp drops (instability) even after the fix; results use the best checkpoint
of each run. Figure: `report/figures/learning_curves.png`.

### 10.4 Generalisation (train on one pattern, test on all): wait per person (s)
| Trained on ↓ / tested on → | Low | Peak | Skewed | Surge |
| --- | --- | --- | --- | --- |
| Low | **9.3** | 25.5 | 12.8 | 16.9 |
| Peak | 24.0 | **21.3** | 20.4 | 25.7 |
| Skewed | **64.4** | 18.6 | **17.7** | 18.1 |
| Surge | 12.7 | 16.4 | 17.6 | **14.9** |
| Randomised demand (DR) | 14.5 | 28.5 | 14.7 | 18.1 |

- Diagonal (matched) average 15.8 s; off-diagonal (mismatched) average 22.8 s, so policies lose performance on
  unfamiliar traffic.
- Worst failure: the policy trained on skewed traffic gets 64.4 s on low traffic.
- Domain randomisation **recovers 55%** of that gap (46% for the maximum-wait metric).
- Formula: gap recovered = (off-diagonal mean − DR mean) / (off-diagonal mean − diagonal mean).

### 10.5 Fairness: what the penalty does (skewed pattern, budget-matched runs)
| Variant | Wait per person (s) | Longest wait (s) |
| --- | --- | --- |
| With fairness penalty (ours) | 15.7 | **115** |
| Without penalty (λ = 0) | **12.9** | 174 |

The penalty cuts the worst wait by **34% (p = 0.029, significant)** and raises the average a little (p = 0.046).
This is the intended trade-off: no road is left waiting for minutes.

### 10.6 Passenger weighting: does the bus get through faster? (peak, budget-matched)
| Variant | Bus delay (s) | Car delay (s) | Wait per person (s) |
| --- | --- | --- | --- |
| Passenger-weighted (ours) | **29.3** | 28.9 | **18.6** |
| Vehicle-count weighting | 37.8 | 34.5 | 24.2 |

Bus delay is 22% lower, but the difference is **not statistically significant (p = 0.17)**; the direction is right,
the evidence is not conclusive.

### 10.7 Ablation study (peak unless noted; wait per person, s)
| Question | Variants (wait per person) | Takeaway |
| --- | --- | --- |
| Which reward works best? | ours 18.6 · waiting-time 20.5 · queue 25.5 · pressure 25.5 | Ours best, but differences not significant (p = 0.49). Queue and pressure rewards are identical at an isolated junction. |
| Bus occupancy assumption | bus = 20: 20.9 · 40: 18.6 · 60: 21.1 | Results are not very sensitive (2.5 s spread). |
| Which observations matter? | full 18.6 · no phase timer 25.8 · no max-wait feature 17.8 | The phase timer matters; the max-wait feature did not help here. |
| Decision interval | 5 s: 18.6 · 10 s: 18.4 · 15 s: 18.4 | No meaningful difference. |
| Sub-lane (mixed traffic) model | on 18.6 · off 78.0 | Turning off lane-filtering cuts junction capacity for every controller (fixed-time 34.2 → 48.3, max-pressure 16.3 → 76.7). The ranking of controllers changes, so modelling mixed traffic matters. |

### 10.8 Vehicle-class delays (peak, seconds)
Ours: two-wheeler 32.7, auto 30.3, car 32.7, bus 32.6. Max-pressure: 26.3, 23.8, 25.6, 27.2. Fixed-time: 44.6,
41.6, 44.1, 45.6.

### 10.9 Illustrative "100 km road" estimate (from the website demo)
A thought experiment: a straight 100 km road with 10 signals (one every 10 km), speed capped at 100 km/h, so 60 min
of free driving. Trip time = 60 min + 10 × (delay a car going straight met at our junction).
- vs fixed-time in the surge pattern: GreenWave saves **5 min 40 s** along the major road (± 2 min 46 s).
- vs the agent without fairness penalty (skewed): GreenWave is **42 s slower** on the major road and **16 s
  faster** on the minor road; both within noise.
- vs max-pressure (peak): GreenWave is ~1 min slower; within noise.
This is arithmetic on measured delays, **not** a corridor simulation (signals assumed independent; delay measured at
50 km/h).

### 10.10 Discussion
- RL clearly beats **fixed-time** signals, especially when traffic changes suddenly (surge), which is exactly the
  weakness of fixed plans.
- Max-pressure is a very strong, training-free rule at a single isolated junction; our agent **ties** it rather than
  beating it. This matches the literature (Ault & Sharon, 2021) and is reported honestly.
- The agent's results vary a lot between training seeds (e.g. peak ± 9.4 s), so more seeds and longer training
  (the "full" profile: 250k steps × 5 seeds) would make conclusions firmer.
- The fairness penalty works as designed: a clear, significant cut in the worst wait for a small average cost.

---

## 11. Observation and Finding

1. **Adaptive beats fixed.** The RL agent reduces waiting per person vs a tuned fixed-time plan by 23% (low), 38%
   (peak), 31% (skewed, not significant) and 59% (surge).
2. **A stale timing plan is costly.** Using the peak plan in the skewed pattern doubles the wait (68.0 s vs 25.7 s).
3. **RL ties max-pressure.** No statistically significant difference in any pattern, on average wait or max wait.
4. **Fairness works.** The penalty cuts the worst wait from 174 s to 115 s (significant) at a cost of ~3 s in the
   average.
5. **Passenger weighting points the right way** (bus delay −22%) but is not statistically conclusive.
6. **Generalisation is a real weakness**: mismatched training costs ~44% more wait on average; one case was 7× worse.
   Domain randomisation recovers about half of the loss.
7. **Mixed-traffic modelling matters.** Without lane-filtering two-wheelers, junction capacity collapses and the
   ranking of controllers changes, so car-only simulations can mislead.
8. **Training stability matters.** Deep Q-learning on this problem collapsed with γ = 0.99; γ = 0.95 and reward
   clipping fixed it. Best-checkpoint selection on held-out seeds is essential.
9. **Throughput is the same for every controller** at these demand levels; the gains are in waiting time, fairness
   and emissions (CO₂ falls with less idling: 187 → 146 g/vehicle in surge vs fixed-time).

---

## 12. Conclusion

GreenWave-RL shows that a deep reinforcement learning agent, trained entirely in simulation on mixed Indian traffic,
can control a signalised junction far better than fixed-time signals, cutting average waiting per person by up to
59% when traffic surges. Its passenger-weighted, fairness-aware reward keeps the worst-off drivers from waiting
excessively, with a significant 34% cut in the longest wait. At a single isolated junction the agent matches, but
does not beat, the classical max-pressure rule; this honest result shows where learning pays off (sudden, uneven
demand) and where a simple rule is already enough. The project also shows that policies degrade on unfamiliar
traffic and that training on randomised demand recovers about half of that loss. Everything is reproducible: one
command regenerates every result, figure and website number from the saved models.

---

## 13. Future Scope

1. **Corridor / network control**: 3-5 connected junctions with multi-agent RL so signals coordinate ("green waves").
2. **Real data**: count vehicles from CCTV video at a real junction (e.g. in Mumbai) and calibrate the simulation.
3. **Camera-based sensing**: replace perfect simulator observations with YOLO-style vehicle detection.
4. **Bus and emergency-vehicle priority** as explicit objectives.
5. **Pedestrian phases** and crossing safety.
6. **Longer, more robust training**: the "full" profile (250k steps × 5 seeds) to reduce variance; algorithms such
   as Rainbow DQN or offline RL.
7. **Sim-to-real deployment study** with safety certification and a hardware-in-the-loop test.

---

## 14. References

1. R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed., MIT Press, 2018.
2. V. Mnih et al., "Human-level control through deep reinforcement learning," *Nature*, 518, 2015.
3. H. van Hasselt, A. Guez and D. Silver, "Deep Reinforcement Learning with Double Q-learning," *AAAI*, 2016.
4. J. Schulman et al., "Proximal Policy Optimization Algorithms," arXiv:1707.06347, 2017.
5. P. Varaiya, "Max pressure control of a network of signalized intersections," *Transportation Research Part C*,
   2013.
6. F. V. Webster, "Traffic Signal Settings," Road Research Technical Paper No. 39, 1958.
7. H. Wei et al., "IntelliLight: A Reinforcement Learning Approach for Intelligent Traffic Light Control," *KDD*,
   2018.
8. H. Wei et al., "PressLight: Learning Max Pressure Control to Coordinate Traffic Signals in Arterial Network,"
   *KDD*, 2019.
9. H. Wei et al., "A Survey on Traffic Signal Control Methods," arXiv:1904.08117, 2019.
10. J. Ault and G. Sharon, "Reinforcement Learning Benchmarks for Traffic Signal Control," *NeurIPS Datasets and
    Benchmarks*, 2021.
11. P. A. Lopez et al., "Microscopic Traffic Simulation using SUMO," *IEEE ITSC*, 2018.
12. Indian Roads Congress, IRC:106-1990, *Guidelines for Capacity of Urban Roads in Plain Areas*.
13. A. Raffin et al., "Stable-Baselines3: Reliable Reinforcement Learning Implementations," *JMLR*, 2021.
14. M. Towers et al., "Gymnasium," 2023 / Farama Foundation.

(Verify exact titles, venues and years before final submission.)

---

## 15. Figures and visuals that already exist (use these in the deck)

All in the project repository:

| File | What it shows | Best slide |
| --- | --- | --- |
| `report/figures/network.png` (also `docs/network.png`) | Plan view of the simulated junction | Dataset / Proposed System |
| `report/figures/main_person_wait.png` | Bar charts: wait per person by controller, 4 patterns | Results |
| `report/figures/main_max_wait.png` | Bar charts: longest wait by controller | Results (fairness) |
| `report/figures/learning_curves.png` | DQN vs Double DQN vs PPO training curves with seed bands | Results |
| `report/figures/generalisation_person_wait.png` | 4×4 heatmap + DR row | Results (generalisation) |
| `report/figures/generalisation_max_wait.png` | Same for longest wait | Results |
| `report/figures/fairness_ecdf.png` | Distribution of per-vehicle wait per reward design | Results (fairness) |
| `report/figures/per_class_delay.png` | Delay per vehicle class per controller | Results |
| `report/figures/ablations.png` | Ablation small multiples | Results |
| `report/figures/co2.png` | CO₂ per vehicle | Results |
| `docs/demo.gif` | Side-by-side replay: fixed-time vs our agent | Proposed System / Demo |
| `web/public/og.png` | Title card with the headline result | Title slide |

Website pages (run `npx serve web/out` and open http://localhost:3000): Home, Demo ("The Arena": two synchronised
replays with per-road wait times and the 100 km estimate), Results, Method, Junction, About. Screenshots of the Demo
and Results pages make strong slides.

Suggested diagrams to draw on slides:
- 8-stage pipeline (Section 6.1).
- Signal timing state machine (Section 6.4).
- RL loop: Agent → action (which road) → SUMO junction → state (queues, waits) + reward → Agent.
- Neural network: 29 → 128 → 128 → 4.

---

## 16. Viva / Q&A preparation

| Likely question | Answer |
| --- | --- |
| Why reinforcement learning and not supervised learning? | There is no dataset of "correct" signal decisions. RL learns from the consequences of its own actions in a simulator. |
| Is your state Markov? | Not strictly: it omits vehicles still upstream. It is partially observable, but queues and waits summarise most of what matters for the next few seconds. |
| Why a replay buffer and a target network? | Consecutive samples are correlated and bootstrapped targets move with every update; both destabilise learning. Replay shuffles data; the target network keeps targets steady. |
| Why Double DQN over DQN? | Taking the maximum of noisy Q-estimates is biased upward. Double DQN lets one network choose the action and the other evaluate it. |
| Why is safety in the environment, not the reward? | A constraint is a guarantee; a penalty is a price the agent might choose to pay. A test verifies min green, yellow and max green over 100 random episodes. |
| Why does max-pressure match your agent? | It is provably throughput-optimal under idealised conditions and needs no training. At one isolated junction there is little left for learning to add; RL's advantage shows in sudden, uneven demand. |
| Why passenger weight 40 for a bus? | Assumed average occupancy. Sensitivity was tested at 20 and 60: results changed by only 2.5 s. |
| Why γ = 0.95 instead of 0.99? | With 0.99 training collapsed; 7 diagnostic runs showed 0.95 stayed stable. It shortens the planning horizon to about 20 decisions (~2 minutes). |
| Why is the end of an episode a truncation, not termination? | Traffic does not stop after one hour; treating it as terminal would bias values near the end. |
| Transitions last 5 s or 13 s; is a constant γ correct? | It is a semi-MDP simplification; an option to discount by elapsed time exists in the code. |
| How do you know it converged? | Validation score on held-out seeds flattening across 3 training seeds, not one training curve. |
| Would this work on a real junction? | Not directly: real sensing is noisy, drivers and pedestrians behave differently, and safety certification is needed. Demand here is synthetic. |
| How is fairness measured? | Longest wait of any vehicle on each road, the 95th-percentile wait, and the full distribution (ECDF). |
| What is domain randomisation? | Training on many randomly scaled traffic patterns so the policy does not over-fit one pattern. It recovered 55% of the generalisation gap. |
| How reproducible is it? | Every random choice is seeded; one command (`python tasks.py all`) regenerates all results, figures and website data from saved models; 30 automated tests and CI. |

Formula to rehearse (Q-learning update):
Q(s, a) ← Q(s, a) + α [ r + γ · max_a′ Q(s′, a′) − Q(s, a) ]

---

## 17. Things NOT to claim (keep the presentation honest)

- Do **not** say the agent "beats max-pressure". It statistically **ties** it in all four patterns.
- Do **not** say passenger weighting "significantly" reduces bus delay. It is −22% but **p = 0.17**.
- Do **not** say it was tested at a real junction or on real traffic data. Demand is **synthetic** and the junction
  is **generic**.
- Do **not** present the 100 km figure as a corridor simulation; it is an **estimate** from one junction.
- Do **not** say domain randomisation "solves" generalisation; it recovers about **half** the loss, and DR performs
  worse than matched training at peak (28.5 s vs 21.3 s).
- Mention that the discount factor and reward clipping were changed from the original plan, and why (Section 7.6).
- The skewed-pattern improvement over fixed-time (17.7 vs 25.7 s) is **not** statistically significant (p = 0.079).

---

## 18. One-slide summary (for the closing or title slide)

**GreenWave-RL** · Fairness-aware deep RL for traffic signals under mixed Indian traffic
- SUMO junction, 4 vehicle classes with lane filtering, left-hand traffic, 4 demand patterns
- Double DQN from scratch + passenger-weighted, fairness-penalised reward
- **−59%** wait per person vs fixed-time in a traffic surge · **−34%** longest wait from the fairness penalty ·
  **ties** max-pressure · domain randomisation recovers **55%** of the generalisation gap
- 58 training runs, 10 unseen test seeds per pattern, Welch t-tests, fully reproducible
