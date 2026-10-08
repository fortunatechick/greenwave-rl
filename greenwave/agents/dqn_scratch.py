"""Double DQN written from scratch in PyTorch (spec Section 7.1). The main agent.

One training step:

    a  = argmax Q(s) w.p. 1-eps else random
    s', r, terminated, truncated = env.step(a)
    buffer.add(s, a, r, s', terminated)
    batch = buffer.sample(64)
    a* = argmax_a' Q_online(s'_b, a')
    y  = r_b + gamma (1 - terminated_b) Q_target(s'_b, a*)
    loss = Huber(Q_online(s_b, a_b), y); clip grads; step Adam
    every 500 steps: theta_target <- theta
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn


@dataclass
class DDQNConfig:
    gamma: float = 0.99
    lr: float = 1e-4
    buffer_size: int = 50_000
    batch_size: int = 64
    target_update: int = 500
    learning_starts: int = 2_000
    train_freq: int = 1
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_fraction: float = 0.5
    grad_clip: float = 10.0
    hidden: tuple[int, ...] = (128, 128)
    smdp_discount: bool = False
    base_dt: float = 5.0


class QNetwork(nn.Module):
    def __init__(self, obs_dim: int, n_actions: int, hidden: tuple[int, ...] = (128, 128)) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        last = obs_dim
        for h in hidden:
            layers += [nn.Linear(last, h), nn.ReLU()]
            last = h
        layers.append(nn.Linear(last, n_actions))
        self.net = nn.Sequential(*layers)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.net(obs)


class ReplayBuffer:
    def __init__(self, capacity: int, obs_dim: int, seed: int = 0) -> None:
        self.capacity = capacity
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.action = np.zeros(capacity, dtype=np.int64)
        self.reward = np.zeros(capacity, dtype=np.float32)
        self.terminated = np.zeros(capacity, dtype=np.float32)
        self.dt = np.full(capacity, 5.0, dtype=np.float32)
        self.size = 0
        self.pos = 0
        self.rng = np.random.default_rng(seed)

    def add(
        self, obs: np.ndarray, action: int, reward: float, next_obs: np.ndarray,
        terminated: bool, dt: float = 5.0,
    ) -> None:  # fmt: skip
        i = self.pos
        self.obs[i], self.next_obs[i] = obs, next_obs
        self.action[i], self.reward[i] = action, reward
        self.terminated[i], self.dt[i] = float(terminated), dt
        self.pos = (i + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int) -> dict[str, torch.Tensor]:
        idx = self.rng.integers(0, self.size, size=batch_size)
        return {
            "obs": torch.from_numpy(self.obs[idx]),
            "next_obs": torch.from_numpy(self.next_obs[idx]),
            "action": torch.from_numpy(self.action[idx]),
            "reward": torch.from_numpy(self.reward[idx]),
            "terminated": torch.from_numpy(self.terminated[idx]),
            "dt": torch.from_numpy(self.dt[idx]),
        }


class DoubleDQN:
    def __init__(self, obs_dim: int, n_actions: int, cfg: DDQNConfig | None = None, seed: int = 0):
        self.cfg = cfg or DDQNConfig()
        self.obs_dim, self.n_actions = obs_dim, n_actions
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        self.q = QNetwork(obs_dim, n_actions, tuple(self.cfg.hidden))
        self.q_target = QNetwork(obs_dim, n_actions, tuple(self.cfg.hidden))
        self.sync_target()
        self.optim = torch.optim.Adam(self.q.parameters(), lr=self.cfg.lr)
        self.buffer = ReplayBuffer(self.cfg.buffer_size, obs_dim, seed)

    def sync_target(self) -> None:
        self.q_target.load_state_dict(self.q.state_dict())

    def epsilon(self, step: int, total_steps: int) -> float:
        c = self.cfg
        frac = min(1.0, step / max(1.0, c.eps_fraction * total_steps))
        return c.eps_start + frac * (c.eps_end - c.eps_start)

    @torch.no_grad()
    def greedy(self, obs: np.ndarray) -> int:
        return int(self.q(torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)).argmax(1).item())

    def act(self, obs: np.ndarray, eps: float) -> int:
        if self.rng.random() < eps:
            return int(self.rng.integers(self.n_actions))
        return self.greedy(obs)

    def td_target(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Double DQN: the online net selects the action, the target net evaluates it.
        `terminated` is 1 only on true termination, never on time-limit truncation."""
        with torch.no_grad():
            best = self.q(batch["next_obs"]).argmax(1, keepdim=True)
            q_next = self.q_target(batch["next_obs"]).gather(1, best).squeeze(1)
            gamma: torch.Tensor | float = self.cfg.gamma
            if self.cfg.smdp_discount:
                gamma = self.cfg.gamma ** (batch["dt"] / self.cfg.base_dt)
            return batch["reward"] + gamma * (1.0 - batch["terminated"]) * q_next

    def update(self) -> float:
        batch = self.buffer.sample(self.cfg.batch_size)
        target = self.td_target(batch)
        q = self.q(batch["obs"]).gather(1, batch["action"].unsqueeze(1)).squeeze(1)
        loss = F.smooth_l1_loss(q, target)
        self.optim.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), self.cfg.grad_clip)
        self.optim.step()
        return float(loss.item())

    def save(self, path: str | Path, extra: dict[str, Any] | None = None) -> None:
        torch.save(
            {
                "state_dict": self.q.state_dict(),
                "obs_dim": self.obs_dim,
                "n_actions": self.n_actions,
                "cfg": asdict(self.cfg),
                "extra": extra or {},
            },
            str(path),
        )

    @classmethod
    def load(cls, path: str | Path) -> DoubleDQN:
        blob = torch.load(str(path), map_location="cpu", weights_only=False)
        cfg = DDQNConfig(**{**blob["cfg"], "hidden": tuple(blob["cfg"]["hidden"])})
        agent = cls(blob["obs_dim"], blob["n_actions"], cfg)
        agent.q.load_state_dict(blob["state_dict"])
        agent.sync_target()
        agent.q.eval()
        return agent
