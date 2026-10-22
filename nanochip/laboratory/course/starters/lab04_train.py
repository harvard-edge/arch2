"""Lab 4: train a small language model and retain its input contract."""


def build_model(config):
    """Build a model compatible with the declared tokenizer and action task."""
    raise NotImplementedError("Implement or replace the model construction component")


def train(
    records,
    output,
    *,
    model_io_contract,
    objective="pretrain",
    base_checkpoint=None,
    **budget,
):
    """Train real parameters and save a reloadable checkpoint plus record."""
    raise NotImplementedError("Implement training with the Lab 1 training partition")
