"""Lab 6: predict candidate outcomes and spend a fixed experiment budget."""


def predict(task, candidate):
    """Return {'metrics': {'cycles': {'value': number, 'unit': 'cycles',
    'uncertainty': nonnegative_number}}}; keep predictions distinct from checks."""
    raise NotImplementedError("Implement a predictor or an explicit baseline")


def choose(task, proposals, history, budget):
    """Choose a legal next experiment using history and remaining budget."""
    raise NotImplementedError("Implement a budgeted search policy")
