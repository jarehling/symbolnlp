"""Guarded, whole-passage alternation grammar and verified derivation graph.

This is NOT an independent NLI model: equivalence follows registered rules plus
explicit trusted assumptions. Every generated node must decode in the same rule.
"""
from collections import deque
from dataclasses import dataclass
import math
import random
import secrets
import unicodedata
from typing import Callable
from .catalog import RULES

ASSUMPTIONS = frozenset(requirement for rule in RULES
                        for group in (rule.requires,) + rule.additional_requirements for requirement in group
                        if requirement != 'bidirectional_entailment')
EntailmentVerifier = Callable[[str, str], bool]


@dataclass(frozen=True)
class RewriteContext:
    assumptions: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, 'assumptions', frozenset(self.assumptions))
        unknown = self.assumptions - ASSUMPTIONS
        if unknown:
            raise ValueError('Unknown rewrite assumption: ' + ', '.join(sorted(unknown)))


def inventory():
    return [rule.evidence() for rule in RULES]


def _frame(rule, slots):
    result = dict(slots)
    if rule.id == 9:
        result['item'], result['item2'] = sorted((slots['item'], slots['item2']))
    if rule.id in {40, 41} and {'item', 'item2', 'item3'} <= slots.keys():
        result['item'], result['item2'], result['item3'] = sorted((slots['item'], slots['item2'], slots['item3']))
    if rule.id == 43:
        result['day'] = str(int(slots['day']))
    return result


def rewrite_catalog(text, *, base_report, candidates, seed, context=None, verifier=None, spelling_style=None):
    context = context or RewriteContext()
    # Preserve line structure so list/prose rules can decode original lists.
    source = unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n').strip()
    initial = next(((rule, rule.decode(source)) for rule in RULES if rule.decode(source) is not None), None)
    if initial is None:
        return None
    initial_rule, slots = initial
    # Rebuild grammar-controlled casing rather than carrying it as an extra
    # source-dependent candidate in the output distribution.
    family = ((initial_rule.forms,) + initial_rule.additional_forms)[slots['_family']]
    form_index = next(i for i, form in enumerate(family) if form.pattern().fullmatch(source))
    source = list(initial_rule.outputs(slots))[form_index]
    queue = deque([source])
    paths = {source: ()}
    edges = []
    matched, enabled, blocked = set(), set(), {}
    rejected, entailment_checks = 0, 0
    while queue:
        current = queue.popleft()
        for rule in RULES:
            slots = rule.decode(current)
            if slots is None:
                continue
            matched.add(rule.id)
            missing = [requirement for requirement in rule.requirements_for(slots)
                       if (verifier is None if requirement == 'bidirectional_entailment'
                           else requirement not in context.assumptions)]
            if missing:
                blocked[rule.id] = sorted(set(blocked.get(rule.id, [])) | set(missing))
                continue
            enabled.add(rule.id)
            for candidate in rule.outputs(slots):
                decoded = rule.decode(candidate)
                if decoded is None or _frame(rule, decoded) != _frame(rule, slots):
                    rejected += 1
                    continue
                if rule.id == 32 and candidate != current:
                    forward, reverse = verifier(current, candidate), verifier(candidate, current)
                    entailment_checks += 2
                    if forward is not True or reverse is not True:
                        rejected += 1
                        continue
                if candidate == current:
                    continue
                edges.append((current, candidate, rule.id))
                if candidate not in paths:
                    if len(paths) >= 4096:
                        raise ValueError('Alternation graph exceeds 4096 renderings; no exhaustive count available')
                    paths[candidate] = paths[current] + ((rule.id, current, candidate),)
                    queue.append(candidate)
        # Union existing symbolic alternatives with catalog rules rather than
        # allowing a newly registered rule to reduce an already supported space.
        from ..rewording.backend import SymbolicBackend
        try:
            space = SymbolicBackend().analyze(current)
        except ValueError:
            space = None
        if space is not None:
            core_methods = []
            parameter_names = {name for name, _ in space.parameters}
            for name, method in [('voice', 12), ('recipient_structure', 13),
                                 ('location_position', 30), ('information_request_form', 33)]:
                if name in parameter_names:
                    core_methods.append(method)
                    matched.add(method)
                    enabled.add(method)
            for variant in space.variants:
                candidate = variant.text
                if candidate == current:
                    continue
                for method in core_methods:
                    edges.append((current, candidate, method))
                if candidate not in paths:
                    if len(paths) >= 4096:
                        raise ValueError('Alternation graph exceeds 4096 renderings')
                    paths[candidate] = paths[current] + ((0, current, candidate),)
                    queue.append(candidate)
    choices = sorted(paths)
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)
    eligible = choices
    if spelling_style is not None:
        eligible = [choice for choice in choices if
                    ('analyse' in choice.lower() or 'colour' in choice.lower()) == (spelling_style == 'uk')]
        if not eligible:
            raise ValueError('Requested document spelling cannot be realized')
    sample = rng.sample(eligible, min(candidates, len(eligible)))
    output = rng.choice(sample)
    path = paths[output]
    # Independent replay against the original text, including every guard and
    # captured semantic slot, rather than trusting enumeration bookkeeping.
    replay = source
    for rule_id, before, after in path:
        if before != replay:
            raise ValueError('Invalid alternation derivation')
        if rule_id == 0:
            from ..core import parse
            from ..rewording.semantics import compare_meaning
            left_doc, right_doc = parse(before), parse(after)
            if len(left_doc.propositions) != 1 or len(right_doc.propositions) != 1 or not compare_meaning(left_doc.propositions[0], right_doc.propositions[0]).exact_match:
                raise ValueError('Core realization replay rejected changed proposition')
            replay = after
            continue
        rule = RULES[rule_id - 1]
        if before != replay:
            raise ValueError('Invalid alternation derivation')
        left, right = rule.decode(before), rule.decode(after)
        if left is None or right is None or _frame(rule, left) != _frame(rule, right):
            raise ValueError('Alternation fidelity replay rejected changed semantic slots')
        if any(requirement not in context.assumptions for requirement in rule.requirements_for(left)
               if requirement != 'bidirectional_entailment'):
            raise ValueError('Missing trusted context during replay')
        replay = after
    if replay != output:
        raise ValueError('Final alternation replay did not reach output')
    statuses = []
    for rule in RULES:
        status = 'enabled' if rule.id in enabled else 'blocked' if rule.id in matched else 'not_matched'
        statuses.append({**rule.evidence(), 'status': status,
                         'missing_context': blocked.get(rule.id, []),
                         'accepted_edges': sum(edge[2] == rule.id for edge in edges)})
    active = [row for row in statuses if row['accepted_edges']]
    report = dict(base_report)
    report['backend'] = 'bounded_alternation_grammar_v1'
    report['canonicalization'] = {
        'operations_applied': ['nfkc_line_endings_outer_whitespace'],
        'scope': 'Preserves internal line structure for lists and discourse rules.',
        'fidelity_reference': 'normalized_input; normalization itself is not semantically verified',
    }
    report['coverage'] = {'complete': True, 'scope': 'whole_passage_bounded_template_grammar',
                          'failures': [], 'opaque_passthrough': False}
    report['selection'] = {**report['selection'], 'candidates_sampled': len(sample),
                            'unchanged_rendering_excluded': False}
    report['variability'] = {
        'choice_parameters': len(active),
        'parameters': [{'parameter': row['name'], 'transformation_id': row['id'],
                        'scope': 'passage', 'accepted_edges': row['accepted_edges']} for row in active],
        'distinct_renderings': str(len(choices)),
        'alternative_renderings_to_input': str(len(choices) - 1),
        'log2_distinct_renderings': math.log2(len(choices)),
        'axes_are_independent': False,
        'count_scope': 'Exact unique nodes reachable under enabled whole-passage grammar rules; not a product of axes.',
        'rejected_candidates': rejected,
    }
    report['meaning'] = {
        'method': 'replayed_rule_derivation', 'score': 1.0,
        'scope': 'Captured template slots and explicit trusted assumptions; not independent semantic similarity.',
        'all_rule_constraints_match': True, 'all_propositions_match': None,
        'general_semantic_similarity': None, 'nli_evaluated': False,
        'external_entailment_evaluated': entailment_checks > 0,
        'external_entailment_calls': entailment_checks,
        'assumptions': sorted(context.assumptions),
        'derivation_transformation_ids': [step[0] if step[0] else 'core_structural_equivalence' for step in path],
    }
    report['alternations'] = {'registered': 45, 'inventory': statuses,
                              'guard_context_source': 'trusted_caller_not_input_text'}
    report['limitations'] = [*report['limitations'],
        'These are bounded whole-passage grammars. Risk labels are advisory, not semantic proofs.',
        'Caller assumptions may permit changes to focus, discourse force, modal strength, or information structure.',
        'The entailment callback is caller-supplied; no NLI model is bundled.']
    return ('unchanged' if output == source else 'reworded', output, report)
