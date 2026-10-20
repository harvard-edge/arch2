"""Lab 5: add bounded context and parse model output into a legal action."""


def serialize(task, history):
    """Represent public workload facts and prior observations as bounded UTF-8 text."""
    raise NotImplementedError("Implement the task-to-model input representation")


def retrieve(query, documents, *, limit):
    """Return bounded, attributed excerpts from permitted documents."""
    raise NotImplementedError("Implement a context provider with source identities")


def parse_action(text, allowed_actions):
    """Return exactly one allowed action or reject malformed output."""
    raise NotImplementedError("Implement a fail-closed action parser")
