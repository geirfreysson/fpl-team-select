# Problem name

FPL Squad Selection via 0-1 Integer Linear Programming (Multi-dimensional Knapsack)

# Goal (pick ONE objective)

**Preferred:** Maximize **projected points** (or performance score) subject to constraints.
**If you truly want to maximize spend:** Maximize **total cost** subject to the same constraints (include points as a tiebreaker).

# Inputs

* `players`: list of objects with fields:

  * `id` (string/int)
  * `name` (string)
  * `team` (string) — Premier League club
  * `position` (string) — one of `GKP, DEF, MID, FWD`
  * `price` (float) — e.g., 5.5 means £5.5m
  * `proj_points` (float) — modelled expected points over target horizon
* `budget`: 100.0 (million)
* `position_requirements`:

  * `GKP`: exactly 2
  * `DEF`: exactly 5
  * `MID`: exactly 5
  * `FWD`: exactly 3
* `club_limit`: max 3 per `team`
* `squad_size`: 15

# Decision variables

* For each player `i`, binary variable `x_i ∈ {0,1}` — 1 if selected in the 15-man squad.

# Constraints

1. **Squad size**:  $\sum_i x_i = 15$
2. **Budget**:      $\sum_i price_i · x_i ≤ 100.0$
3. **Positions**:

   * $\sum_{i:pos=GKP} x_i = 2$
   * $\sum_{i:pos=DEF} x_i = 5$
   * $\sum_{i:pos=MID} x_i = 5$
   * $\sum_{i:pos=FWD} x_i = 3$
4. **Club cap** (for each club c): $\sum_{i:team=c} x_i ≤ 3$

# Objective (choose one)

* **Max points:** maximize $\sum_i proj\_points_i · x_i$
* **Max spend:** maximize $\sum_i price_i · x_i$

  * **Tiebreaker:** prefer higher projected points:
    maximize $\sum_i (price_i · x_i) + ε·(proj\_points_i · x_i)$ with very small $ε$ (e.g., 1e-6).

# Output

* `selected_ids`: list of 15 player IDs
* `total_price`: sum of prices
* `total_proj_points`: sum of projected points
* `by_position`: mapping from position to selected players
* `by_team_counts`: mapping from team to count
* Validation flags that all constraints are met.

# Implementation requirements for the LLM

* Use a standard ILP solver (Python: **OR-Tools**, **PuLP**/**CBC**, or **mip**/**GLPK**).
* Encode variables and constraints exactly as above.
* Ensure numeric precision (prices may be in 0.1 increments; consider scaling by 10 to use integers if solver struggles).
* If infeasible, return a helpful error (e.g., if inputs are filtered oddly).
* Provide a quick unit test with a tiny fake dataset to prove constraints.

# Optional refinements (include only if you want them)

* **Bench weighting:** If you care about bench value, apply weights: starters weight=1.0, bench weight=β (e.g., 0.2). This needs extra variables that pick an XI; otherwise skip.
* **Risk/rotation penalty:** subtract a small penalty for low minutes probability or high injury risk.
* **Captaincy preview:** if optimizing for next GW XI, double the max-projected player’s contribution (requires XI selection variables).

# Example acceptance test (tiny)

* Budget 10.0, need GKP=1, DEF=1, MID=1, FWD=1, squad\_size=4, club\_limit=2.
* Provide 6–8 dummy players with clear best combination; verify solver picks the combo meeting all constraints and maximizing the stated objective.

---

## What to call the algorithm

> **“Binary Integer Linear Programming (0-1 ILP) formulation of the FPL team selection problem (a multi-dimensional knapsack).”**

If you want a greedy baseline to compare against (not optimal but fast): sort by `proj_points / price` within each position and fill quotas under budget and club caps — but for the real solution, use the ILP above.
