"""Optional CPU learning components; importing this package does not import torch.

This is a tiny structured sequence decoder, not a pretrained language model.
PyTorch is required only when training or loading a checkpoint.
"""

from .sequence import TinyActionDecoder, evaluate, load_model, train
from .proposer import LearnedProposer

__all__ = ["LearnedProposer", "TinyActionDecoder", "evaluate", "load_model", "train"]
