from ...contracts import ContractError, file_sha256


def summarize_physical_receipt(raw, candidate_sha256):
    if not isinstance(raw, dict) or raw.get("candidate_sha256") != candidate_sha256:
        raise ContractError(
            "Physical receipt does not identify the evaluated candidate"
        )
    checks = raw.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ContractError("Physical receipt needs named check results")
    for check in checks:
        if not all(
            isinstance(check.get(key), str) and check[key]
            for key in ("name", "status", "scope")
        ):
            raise ContractError("Physical checks need names, states, and scope")
        if check["status"] not in ("pass", "fail", "unresolved", "not_run"):
            raise ContractError("Unknown physical check state")
    return {
        "candidate_sha256": candidate_sha256,
        "completed": raw.get("status") == "completed",
        "checks": checks,
        "all_required_passed": raw.get("ok") is True
        and all(c["status"] == "pass" for c in checks),
        "physical_receipt_sha256": raw.get("receipt_sha256"),
    }
