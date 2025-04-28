"""
This module provides a way to safely import PyTorch-related modules
to prevent conflicts with Streamlit's file watcher
"""

import sys
import importlib
from functools import wraps

# Store original import system
_original_import = __import__

def lazy_import(name):
    """
    Create a lazy loader for a module to defer import until actually needed
    """
    class LazyModule:
        def __init__(self, module_name):
            self.module_name = module_name
            self._module = None
            
        def __getattr__(self, attr):
            if self._module is None:
                # Only import when an attribute is actually accessed
                self._module = importlib.import_module(self.module_name)
            return getattr(self._module, attr)
    
    return LazyModule(name)

# Dictionary to store torch-related modules
torch_modules = {
    'torch': lazy_import('torch'),
    'torch.nn': lazy_import('torch.nn'),
    'torch.optim': lazy_import('torch.optim'),
    'torchvision': lazy_import('torchvision'),
    'torchvision.transforms': lazy_import('torchvision.transforms'),
}

def get_torch():
    """Safe way to import torch without Streamlit segfaults"""
    return torch_modules['torch']

def with_safe_torch_import(func):
    """
    Decorator to make a function use safe torch imports
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Use lazy imported torch modules for this function execution
        return func(*args, **kwargs)
    return wrapper