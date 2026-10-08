// LaTeX sources, shared by the home and method pages.
export const TEX = {
  rewardWait: String.raw`r_t^{\text{wait}} = \frac{1}{\kappa}\big(W_{t-1} - W_t\big)`,
  rewardOurs: String.raw`r_t = \frac{1}{\kappa}\sum_{c} w_c \,\big(W_{c,t-1} - W_{c,t}\big) \;-\; \lambda \,\frac{\max\!\big(0,\; \max_{a} \text{wait}_a - T\big)}{T}`,
  dqnLoss: String.raw`L(\theta) = \mathbb{E}\Big[\big(r + \gamma \max_{a'} Q_{\theta^-}(s', a') - Q_\theta(s, a)\big)^2\Big]`,
  ddqnTarget: String.raw`y = r + \gamma \,(1 - d)\; Q_{\theta^-}\!\big(s', \arg\max_{a'} Q_\theta(s', a')\big)`,
  webster: String.raw`C_0 = \frac{1.5\,L + 5}{1 - Y}, \qquad Y = \sum_i y_i,\quad y_i = \frac{q_i}{s_i}`,
  pressure: String.raw`p(\phi) = \sum_{(l,m) \in \phi} \big(q_l^{\text{in}} - q_m^{\text{out}}\big)`,
  gap: String.raw`\text{gap recovered} = \frac{\overline{\text{off-diagonal}} - \overline{\text{DR}}}{\overline{\text{off-diagonal}} - \overline{\text{diagonal}}}`,
};
