"""Lab 3: parse receipts without confusing tool errors with design failures."""


def adapt_receipt(raw, task, candidate):
    """Return a typed receipt only when candidate and task identities match."""
    raise NotImplementedError("Implement identity-bound receipt parsing")


def summarize_cost(receipts):
    """Aggregate recorded cost while retaining evidence mode and status."""
    raise NotImplementedError("Implement evidence-aware cost aggregation")
