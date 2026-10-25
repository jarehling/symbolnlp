"""Compose bounded alternation units with existing symbolic sentences.

Units keep their order. Longest matching discourse units bind their reference
and temporal context before any within-unit split/merge transformations.
"""
from dataclasses import asdict
import math
import random
import secrets
import unicodedata
from .catalog import RULES
from .engine import RewriteContext, rewrite_catalog


def rewrite_mixed(text, *, base_report, candidates, seed, context=None, verifier=None):
    from ..core import parse, split_sentences
    from ..rewording.backend import SymbolicBackend
    from ..rewording.semantics import compare_meaning
    source = unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n').strip()
    remaining, units, has_catalog = source, [], False
    while remaining:
        ends = []
        for rule in RULES:
            for group in (rule.forms,) + rule.additional_forms:
                for form in group:
                    match = form.pattern().match(remaining)
                    if match and rule.decode(match.group()) is not None and (match.end() == len(remaining) or remaining[match.end()].isspace()):
                        # A noun-phrase fragment may not absorb the beginning of
                        # an unparsed clause. Only full terminated units can split.
                        if match.end() == len(remaining) or remaining[:match.end()].endswith(('.', '?')):
                            ends.append(match.end())
        if ends:
            end = max(ends)
            units.append(('catalog', remaining[:end]))
            has_catalog = True
            remaining = remaining[end:].lstrip()
        else:
            try:
                sentence = split_sentences(remaining)[0]
                parse(sentence)
            except ValueError:
                return None  # caller's standard coverage path rejects the passage
            if not remaining.startswith(sentence):
                # A final unterminated core sentence is allowed.
                if sentence[:-1] != remaining:
                    return None
                remaining = ''
            else:
                remaining = remaining[len(sentence):].lstrip()
            units.append(('symbolic', sentence))
        if len(units) > 1000:
            raise ValueError('At most 1000 semantic units per passage')
    if not has_catalog:
        return None
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)
    context = context or RewriteContext()
    outputs, reports, counts, axes = [], [], [], []
    spelling_units = [i for i, (kind, unit) in enumerate(units)
                      if kind == 'catalog' and RULES[44].decode(unit) is not None]
    document_spelling = rng.choice(['us', 'uk']) if spelling_units else None
    # Draw one candidate for each unit; the joint distribution is uniform over
    # the product. Seeds are derived privately, not from source wording.
    for index, (kind, unit) in enumerate(units):
        if kind == 'catalog':
            result = rewrite_catalog(unit, base_report=base_report, candidates=candidates,
                                     seed=None if seed is None else rng.getrandbits(128),
                                     context=context, verifier=verifier,
                                     spelling_style=document_spelling if index in spelling_units else None)
            if result is None:
                raise ValueError('Catalog unit no longer decodes')
            _, output, report = result
            outputs.append(output)
            reports.append(report)
            count = int(report['variability']['distinct_renderings'])
            if index in spelling_units and index != spelling_units[0]:
                count //= 2
            counts.append(count)
            axes.extend({**axis, 'unit': index + 1,
                         'scope': 'document' if axis.get('transformation_id') == 45 else 'unit'}
                        for axis in report['variability']['parameters']
                        if axis.get('transformation_id') != 45 or index == spelling_units[0])
        else:
            space = SymbolicBackend().analyze(unit)
            selected = rng.choice(space.variants)
            output = selected.text
            fidelity = compare_meaning(parse(unit).propositions[0], parse(output).propositions[0])
            if not fidelity.exact_match:
                raise ValueError('Mixed passage core fidelity gate rejected output')
            outputs.append(output)
            reports.append({'meaning': asdict(fidelity)})
            counts.append(len(space.variants))
            axes.extend({'unit': index + 1, 'parameter': name, 'values': list(values)}
                        for name, values in space.parameters)
    output = ' '.join(outputs)
    total = math.prod(counts)
    aggregate = {}
    for report in reports:
        for row in report.get('alternations', {}).get('inventory', []):
            if row['id'] not in aggregate:
                aggregate[row['id']] = {**row, 'sites': []}
    for index, report in enumerate(reports):
        for row in report.get('alternations', {}).get('inventory', []):
            if row['status'] != 'not_matched':
                record = aggregate[row['id']]
                record['sites'].append({'unit': index + 1, 'status': row['status'],
                                        'missing_context': row['missing_context'],
                                        'accepted_edges': row['accepted_edges']})
                if row['status'] == 'enabled' or record['status'] == 'not_matched':
                    record['status'] = row['status']
    report = dict(base_report)
    report['backend'] = 'mixed_bounded_grammar_v1'
    report['canonicalization'] = {'operations_applied': ['nfkc_line_endings_outer_whitespace'],
                                  'scope': 'Internal line structure preserved; semantic units retain order.'}
    report['selection'] = {**report['selection'], 'method': 'independent_uniform_semantic_unit_sampling',
                            'unchanged_rendering_excluded': False}
    report['coverage'] = {'complete': True, 'semantic_units': len(units),
                          'unit_types': [kind for kind, _ in units], 'failures': []}
    report['variability'] = {'choice_parameters': len(axes), 'parameters': axes,
                             'distinct_renderings': str(total), 'log2_distinct_renderings': math.log2(total),
                             'per_unit_renderings': counts, 'axes_are_independent': False,
                             'count_scope': 'Exact product of verified unit counts, with shared document spelling counted once; unit order retained.'}
    report['meaning'] = {'method': 'unit_local_rule_replay_and_structural_comparison', 'score': 1.0,
                          'general_semantic_similarity': None, 'unit_evidence': [r['meaning'] for r in reports],
                          'scope': 'Registered rule assumptions plus encoded core fields; not independent NLI.',
                          'nli_evaluated': False,
                          'external_entailment_evaluated': any(r['meaning'].get('external_entailment_evaluated', False) for r in reports)}
    report['alternations'] = {'registered': 45, 'inventory': list(aggregate.values()),
                              'guard_context_source': 'trusted_caller_not_input_text'}
    report['limitations'] = [*report['limitations'],
        'Whole-passage enumeration applies only inside registered grammar units; unit order is fixed.',
        'Reported diversity is conditional on explicit caller assumptions, not proof of semantic equivalence.']
    return ('unchanged' if output == source else 'reworded', output, report)
