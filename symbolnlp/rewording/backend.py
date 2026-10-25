"""Bounded symbolic paraphrase backend; replaceable independently of the pipeline."""
from dataclasses import dataclass, replace
from itertools import product
from typing import Protocol
from ..core import Adjunct, Document, INTRANSITIVE, Proposition, VERBS, parse, render, render_entity
from .semantics import compare_meaning
from .realizations import extra_variants


@dataclass(frozen=True)
class Variant:
    text: str
    # Labels describe available choices, not secrets used for selection.
    choices: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SentenceSpace:
    source: Proposition
    variants: tuple[Variant, ...]
    rejected_candidates: int
    parameters: tuple[tuple[str, tuple[str, ...]], ...]


class RewriteBackend(Protocol):
    name: str

    def analyze(self, sentence: str) -> SentenceSpace: ...


class SymbolicBackend:
    name = 'controlled_english_symbolic_v1'

    def analyze(self, sentence: str) -> SentenceSpace:
        document = parse(sentence)
        if len(document.propositions) != 1:
            raise ValueError('Backend requires exactly one sentence')
        original = document.propositions[0]
        def canonical_entity(entity):
            if entity is not None and (entity.noun or entity.pronoun or entity.nominalized_adjective):
                return replace(entity, text=None)
            return entity
        roles = {name: canonical_entity(getattr(original, name)) for name in
                 ('agent', 'patient', 'recipient', 'subject', 'related_to', 'complement', 'experiencer')}
        source = replace(original, **roles,
                         adjuncts=tuple(Adjunct(a.preposition, canonical_entity(a.entity)) for a in original.adjuncts))
        lemmas = [forms[0] for forms in VERBS[source.sense]] if source.sense in VERBS else [None]
        voices = ['active', 'passive'] if (source.sense in VERBS and
                  source.sense not in INTRANSITIVE and source.agent is not None and
                  source.mood != 'imperative' and (not source.question or source.question.kind == 'polar')) else ['canonical']
        # Combining fronting and double-object syntax is safe only when both
        # choices are applicable. Invalid combinations are removed by verification.
        locations = ['trailing', 'fronted'] if source.adjuncts and not source.question else ['trailing']
        recipients = ['to', 'double_object'] if source.recipient and not source.question else ['to']
        accepted = {}
        rejected = 0
        for lemma, voice, location, recipient in product(lemmas, voices, locations, recipients):
            prop = replace(source, lexical_form=lemma)
            text = render(Document((prop,)), vocabulary='preserve',
                          structure='active' if voice == 'canonical' else voice)
            if recipient == 'double_object':
                if voice == 'passive':
                    continue
                # Construct from roles, avoiding any search/replace on source text.
                target = ' to ' + render_entity(source.recipient, case='object')
                theme = render_entity(source.patient, case='object')
                ending = ' ' + theme + target
                # All event adjuncts/adverbs follow this complete argument string.
                at = text.find(ending)
                if at < 0:
                    continue
                text = text[:at] + ' ' + render_entity(source.recipient, case='object') + ' ' + theme + text[at + len(ending):]
            if location == 'fronted':
                first = source.adjuncts[0]
                phrase = first.preposition + ' ' + render_entity(first.entity, case='object')
                # Regenerate the clause without the first adjunct. This also
                # preserves capitalization of names such as Alice and I.
                clause = text
                at = clause.rfind(' ' + phrase)
                if at < 0:
                    continue
                clause = clause[:at] + clause[at + len(phrase) + 1:]
                # Only lower a generated common-noun/pronoun initial, never a name.
                subject = source.patient if voice == 'passive' else source.agent
                if source.mood == 'imperative' or (subject and
                    (subject.noun or subject.nominalized_adjective or
                     (subject.pronoun and subject.pronoun != 'i'))):
                    clause = clause[0].lower() + clause[1:]
                text = phrase[0].upper() + phrase[1:] + ', ' + clause
            for candidate, extra_choices in extra_variants(source, text):
                try:
                    decoded = parse(candidate).propositions[0]
                    if not compare_meaning(source, decoded).exact_match:
                        rejected += 1
                        continue
                except ValueError:
                    rejected += 1
                    continue
                choices = (('verb_lemma', lemma or 'fixed'), ('voice', voice),
                           ('location_position', location), ('recipient_structure', recipient)) + extra_choices
                accepted.setdefault(candidate, Variant(candidate, choices))
        if not accepted:
            raise ValueError('No structurally equivalent rendering available')
        parameters = []
        for name in sorted({name for variant in accepted.values() for name, _ in variant.choices}):
            values = tuple(sorted({dict(v.choices)[name] for v in accepted.values()}))
            if len(values) > 1:
                parameters.append((name, values))
        return SentenceSpace(original, tuple(accepted.values()), rejected, tuple(parameters))
