"""Numpy-backed stand-in for the few torch calls that SPCI_class.py and data.py (hamrel-cxu/SPCI-code,
commit d598dd3) make on the random-forest path: tensors used as containers only, with no autograd
and no MLP. Used by spci_ipis.py only, which puts this folder first on sys.path.
"""

import numpy as _np


class Tensor(_np.ndarray):
    def __getitem__(self, key):
        out = super().__getitem__(key)
        if not isinstance(out, _np.ndarray):  # a scalar: torch returns a 0-d tensor
            out = _np.asarray(out).view(Tensor)
        return out

    def cpu(self):
        return self

    def detach(self):
        return self

    def numpy(self):
        return _np.asarray(self)

    def to(self, *args, **kwargs):
        return self

    def float(self):
        return self.astype(_np.float32).view(Tensor)


def from_numpy(a):
    return _np.asarray(a).view(Tensor)


def vstack(seq):
    return _np.vstack([_np.asarray(s) for s in seq]).view(Tensor)


def hstack(seq):
    return _np.hstack([_np.asarray(s) for s in seq]).view(Tensor)


def device(name):
    return name


class _Cuda:
    @staticmethod
    def is_available():
        return False


cuda = _Cuda()
