"""Placeholders: SPCI_class.py defines an MLP at import time; the random-forest path never builds it."""


class Module:
    pass


class _Unused:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("torch.nn is not available in this shim (the MLP path is not used)")


class Linear(_Unused):
    pass


class ReLU(_Unused):
    pass


class Sequential(_Unused):
    pass
