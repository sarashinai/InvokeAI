from __future__ import annotations

from contextlib import nullcontext
from typing import Literal, Optional, Union

import torch
from torch import autocast

from invokeai.app.services.config.config_default import PRECISION, get_config

CPU_DEVICE = torch.device("cpu")
CUDA_DEVICE = torch.device("cuda")
MPS_DEVICE = torch.device("mps")


def choose_torch_device() -> torch.device:
    """Convenience routine for guessing which GPU device to run model on"""
    config = get_config()
    if config.device == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return CPU_DEVICE
    else:
        return torch.device(config.device)


def get_torch_device_name() -> str:
    device = choose_torch_device()
    return torch.cuda.get_device_name(device) if device.type == "cuda" else device.type.upper()


def choose_precision(device: torch.device) -> Literal["float32", "float16", "bfloat16"]:
    """Return an appropriate precision for the given torch device."""
    app_config = get_config()
    if device.type == "cuda":
        device_name = torch.cuda.get_device_name(device)
        if "GeForce GTX 1660" in device_name or "GeForce GTX 1650" in device_name:
            # These GPUs have limited support for float16
            return "float32"
        elif app_config.precision == "auto" or app_config.precision == "autocast":
            # Default to float16 for CUDA devices
            return "float16"
        else:
            # Use the user-defined precision
            return app_config.precision
    elif device.type == "mps":
        if app_config.precision == "auto" or app_config.precision == "autocast":
            # Default to float16 for MPS devices
            return "float16"
        else:
            # Use the user-defined precision
            return app_config.precision
    # CPU / safe fallback
    return "float32"


def torch_dtype(device: Optional[torch.device] = None) -> torch.dtype:
    device = device or choose_torch_device()
    precision = choose_precision(device)
    if precision == "float16":
        return torch.float16
    if precision == "bfloat16":
        return torch.bfloat16
    else:
        # "auto", "autocast", "float32"
        return torch.float32


def choose_autocast(precision: PRECISION):
    """Returns an autocast context or nullcontext for the given precision string"""
    # float16 currently requires autocast to avoid errors like:
    # 'expected scalar type Half but found Float'
    if precision == "autocast" or precision == "float16":
        return autocast
    return nullcontext


def normalize_device(device: Union[str, torch.device]) -> torch.device:
    """Ensure device has a device index defined, if appropriate."""
    device = torch.device(device)
    if device.index is None:
        # cuda might be the only torch backend that currently uses the device index?
        # I don't see anything like `current_device` for cpu or mps.
        if device.type == "cuda":
            device = torch.device(device.type, torch.cuda.current_device())
    return device
