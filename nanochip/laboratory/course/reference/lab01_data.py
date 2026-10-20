from ..components import split_by_group


def split_records(records, *, seed, fractions=None):
    return split_by_group(records, seed=seed, fractions=fractions)
