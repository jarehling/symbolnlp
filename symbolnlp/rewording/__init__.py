"""Paraphrasing with explicit variation and fidelity reports."""
from .pipeline import ParaphraseResult, paraphrase
from .semantics import Fidelity, compare_meaning
from .artifacts import inspect_surface

__all__ = ['ParaphraseResult', 'paraphrase', 'Fidelity', 'compare_meaning', 'inspect_surface']
