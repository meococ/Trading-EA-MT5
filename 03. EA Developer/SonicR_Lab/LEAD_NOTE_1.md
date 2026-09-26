# LEAD NOTE 1 - F0 parity must copy the run AS CODED (Lead, 23/09 15:57Z)

Your log says `sr.blocked` was telemetry (not a gate) in the real EA, and that you plan to implement W2 as a gate
inside F0 "per the brief". Do not. The brief's description of J came from the 16/08 packet spec; the known-answer
test needs the object that actually produced run 20260816_205426 (N=307, PF 0.94).

- F0 = the 16/08 build exactly as it ran (recover it from git history read-only: `git log` / `git show <rev>:<path>`;
  never checkout, stash, reset or otherwise change the working tree). Every rule that was telemetry in that build
  stays telemetry in F0 (logged as a flag, not filtering trades). Record the commit/rev you used in PARITY_J.md.
- W2 as a GATE belongs only to the ladder step "+W2" (and to the full composite). That is exactly the point of the
  ladder: measure what the gate adds on top of the coded J.
- If the brief and the as-coded build differ anywhere else, F0 follows the build; list every difference in
  PARITY_J.md so the ladder steps are defined relative to the real J.
- Also record in PARITY_J.md the run's symbol, window, cost settings and tester model you found, since the parity
  tolerance (N within 20%, PF within 0.15) is judged on the same window.
