"""Non-LLM, controlled-English proposition parser and generator."""
from .core import Question, QueryContext, Measurement, Adjunct, Document, Entity, Proposition, UnsupportedText, parse, render, render_entity

__all__ = ["Question", "QueryContext", "Measurement", "Adjunct", "Document", "Entity", "Proposition", "UnsupportedText", "parse", "render", "render_entity", "ParaphraseResult", "paraphrase", "compare_meaning", "RewriteContext"]

from .rewording import ParaphraseResult, paraphrase, compare_meaning

from .alternations import RewriteContext
