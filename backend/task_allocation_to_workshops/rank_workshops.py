# rank_workshops.py: rank the allowed workshops with one objective. In the plan, only on-time
# workshops are ranked.
#
# Allocation flow: recommend_one_task -> workshop_rules_and_estimates (metrics) -> [rank_workshops].
# Came from:       notebook 05, Section 11 (DEFAULT_OBJECTIVE from Section 1).
# Reads:           candidate metrics given as arguments.
# Writes:          nothing (pure calculations).

# Ranking for a request without a preference.
DEFAULT_OBJECTIVE = "minimize_tardiness"
# Each tuple lists the main metric, then the tie-breakers. Every metric is minimized.
OBJECTIVE_FIELDS = {
    "minimize_tardiness": ("tardiness_days", "eta_days", "cost"),
    "minimize_cost": ("cost", "eta_days", "defect_rate"),
    "minimize_defects": ("defect_rate", "eta_days", "cost"),
    "minimize_concentration": ("share", "eta_days", "defect_rate"),
    "minimize_robustness": ("share", "tardiness_days", "defect_rate"),
}
# Alternate spellings of the same objectives. They do not add new objectives.
OBJECTIVE_ALIASES = {
    "minimise_lateness": "minimize_tardiness",
    "minimise_cost": "minimize_cost",
    "minimise_defects": "minimize_defects",
    "minimise_concentration": "minimize_concentration",
    "minimise_robustness": "minimize_robustness",
}
# Each request's preference selects its objective, unless PLAN_OBJECTIVE (config.toml) replaces it.
PREFERENCE_OBJECTIVES = {"none": DEFAULT_OBJECTIVE, "fastest": "minimize_tardiness",
                         "cheapest": "minimize_cost", "quality": "minimize_defects"}
# Experimental weights for the hybrid objective: lateness, cost and workload share, after scaling.
DEFAULT_HYBRID_WEIGHTS = {"tardiness_days": 0.5, "cost": 0.25, "share": 0.25}


def hybrid_score(candidate, all_metrics, weights):
    """Return one workshop's hybrid score: its scaled metric values, blended. Smaller is better.

    Each metric is scaled to 0..1 within these candidates, so money, days and fractions can be
    added. When all values are equal, the metric adds zero (nothing is divided by zero).
    """
    score = 0.0
    for field, weight in weights.items():
        values = [metrics[field] for metrics in all_metrics.values()]
        low, high = min(values), max(values)
        span = high - low if high > low else 1.0
        score += weight * (candidate[field] - low) / span
    return score


def rank_candidates(metrics, objective, weights):
    """Rank the workshops under one objective.

    metrics maps workshop ID -> candidate_metrics; weights are used by "hybrid" only.
    Returns (ranking, keys): workshop IDs best first, and the key that ranked each one. Hybrid gives
    one score per workshop; the other objectives compare metric tuples from left to right. Smaller
    keys win, and equal keys keep workshops.csv order. The keys are saved as evidence.
    """
    if objective == "hybrid":
        # Round only the blended score, so floating-point noise cannot break a real tie.
        keys = {wid: round(hybrid_score(row, metrics, weights), 12) for wid, row in metrics.items()}
    else:
        fields = OBJECTIVE_FIELDS[objective]
        keys = {wid: tuple(row[field] for field in fields) for wid, row in metrics.items()}
    ranking = sorted(keys, key=keys.get)
    return ranking, keys
