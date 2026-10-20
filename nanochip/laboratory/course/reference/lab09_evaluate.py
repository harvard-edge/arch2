from ..components import summarize_cost
from ...contracts import ContractError, RunReceipt


def compare_campaigns(campaigns, *, evaluation_groups, campaign_cost):
    if not campaigns or not evaluation_groups:
        raise ContractError("Campaigns and declared evaluation groups are required")
    names = [item.get("method") for item in campaigns]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ContractError("Comparison methods need distinct names")
    group_sets = [set(item.get("groups", ())) for item in campaigns]
    if any(groups != set(evaluation_groups) for groups in group_sets):
        raise ContractError("Every method must use the same declared evaluation groups")
    output_methods = []
    for item in campaigns:
        case_summaries = []
        all_receipts = []
        for case in item.get("cases", ()):
            receipts = [outcome["receipt"] for outcome in case.get("outcomes", ())
                        if outcome.get("receipt") is not None]
            receipts = [RunReceipt(**raw) if isinstance(raw, dict) else raw for raw in receipts]
            all_receipts.extend(receipts)
            case_summaries.append({
                "case_id": case["case_id"], "group_id": case["group_id"],
                "objective": case["objective"], "candidate_budget": case["candidate_budget"],
                "outcome_count": len(case.get("outcomes", ())),
                "eligible_count": sum(bool(row.get("eligible")) for row in case.get("outcomes", ())),
                "best": case.get("best"), "attempt_cost": case["attempt_cost"],
                "tool_receipt_cost": summarize_cost(tuple(receipts)) if receipts else None,
            })
        output_methods.append({
            "method": item["method"], "groups": item["groups"],
            "objective": item["objective"], "candidate_budget": item["candidate_budget"],
            "outcome_count": sum(row["outcome_count"] for row in case_summaries),
            "eligible_count": sum(row["eligible_count"] for row in case_summaries),
            "cases": case_summaries,
            "attempt_cost": item["attempt_cost"],
            "tool_receipt_cost": summarize_cost(tuple(all_receipts)) if all_receipts else None,
        })
    return {
        "evaluation_groups": sorted(evaluation_groups),
        "methods": output_methods,
        "campaign_cost": campaign_cost,
        "cost_allocation": {
            "campaign_cost": "shared_campaign_total_reported_once",
            "method_costs": "overlapping_breakdowns_not_additive",
        },
        "interpretation": "Descriptive matched-campaign comparison; no causal claim follows from one campaign.",
    }
