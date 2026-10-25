"""Transparent structural fidelity checks; not a general English similarity model."""
from dataclasses import asdict, dataclass, fields
from ..core import Proposition


def _semantic_value(value):
    if isinstance(value, dict):
        result = {k: _semantic_value(v) for k, v in value.items() if k != 'lexical_form'}
        # Surface text is redundant for structured noun/pronoun entities.
        # Proper names represented only as text remain identity-bearing.
        if 'text' in result and any(result.get(k) is not None for k in
                                    ('noun', 'pronoun', 'nominalized_adjective')):
            result.pop('text')
        return result
    if isinstance(value, (list, tuple)):
        return [_semantic_value(v) for v in value]
    return value


@dataclass(frozen=True)
class Fidelity:
    method: str
    score: float
    exact_match: bool
    matched_fields: int
    compared_fields: int
    differing_fields: tuple[str, ...]
    scope: str = 'encoded_proposition_fields_only'


def compare_meaning(source: Proposition, candidate: Proposition) -> Fidelity:
    """Equal-weight agreement of top-level semantic fields.

    score=1 means matching encoded structures, not a calibrated probability of
    human-perceived equivalence. Critical mismatches always fail the filter,
    regardless of how many other fields match.
    """
    left, right = _semantic_value(asdict(source)), _semantic_value(asdict(candidate))
    names = [f.name for f in fields(Proposition) if f.name != 'lexical_form']
    differing = tuple(name for name in names if left[name] != right[name])
    return Fidelity('structural_field_agreement', (len(names) - len(differing)) / len(names),
                    not differing, len(names) - len(differing), len(names), differing)
