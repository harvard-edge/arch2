"""Lab 9: compare frozen methods on independent campaigns and recorded cost."""


def compare_campaigns(campaigns, *, evaluation_groups, campaign_cost):
    """Compare the four frozen methods on the same held-out groups.

    Each ``campaigns`` item contains ``method``, ``groups``, ``objective``
    (metric, scope, minimize, and unit), ``candidate_budget``, and ``cases``.
    Each case contains its case/group IDs, objective, budget, measured
    ``outcomes``, the measured ``best`` candidate (or ``None``),
    ``attempt_cost``, and ``tool_receipt_cost``. The method record also carries
    aggregate method costs. The shared campaign-level
    preparation/training ledger arrives once in the required ``campaign_cost``
    keyword argument. Per-method attempt and tool costs remain separate from
    that shared ledger and may overlap with broader campaign totals.

    Return a mapping with sorted ``evaluation_groups``, the unchanged top-level
    ``campaign_cost``, a ``cost_allocation`` mapping declaring the shared total
    once and per-method costs as overlapping nonadditive breakdowns, and four
    ``methods``.
    The required ``cost_allocation`` value is exactly::

        {"campaign_cost": "shared_campaign_total_reported_once",
         "method_costs": "overlapping_breakdowns_not_additive"}

    Each method must preserve its name, groups, objective and unit, candidate
    budget, eligible/outcome counts, per-case measured best (or no-feasible
    result), per-method attempt cost, and tool-receipt cost. Include a concise
    interpretation, but do not claim a causal benefit
    from one comparison.
    """
    raise NotImplementedError("Implement held-out campaign comparison")
