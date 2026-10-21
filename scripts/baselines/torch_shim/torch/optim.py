"""Placeholder: only the MLP path uses an optimiser."""


class Adam:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("torch.optim is not available in this shim")
