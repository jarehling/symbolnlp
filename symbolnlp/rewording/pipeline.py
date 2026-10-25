"""Analyze -> enumerate/filter -> privately sample -> audit a paraphrase.

Only text is intended for the receiving agent. Reports belong on a separate
trusted audit path; forwarding input-dependent metrics creates another channel.
"""
from dataclasses import asdict, dataclass
import math
import random
import secrets
from .backend import RewriteBackend, SymbolicBackend
from .artifacts import inspect_surface
from .canonical import canonicalize
from .semantics import compare_meaning
from ..core import parse, split_sentences

LIMITATIONS = (
    'Controlled grammar only; unsupported passages produce no output.',
    'Meaning scores measure encoded structure, not general semantic equivalence or calibrated confidence.',
    'Variability bits describe available output choices, not measured residual covert-channel capacity.',
    'No watermark detector, attribution probe, or adversarial encoder/decoder evaluation has run.',
    'Meaning, sentence order, entity choices, and passage length may retain signals.',
    'Keep this report on a trusted audit path; send only text to the receiving agent.',
)


@dataclass(frozen=True)
class ParaphraseResult:
    status: str
    text: str | None
    report: dict

    def to_dict(self):
        return asdict(self)


def _unrank(index, spaces):
    indices = []
    for space in reversed(spaces):
        index, position = divmod(index, len(space.variants))
        indices.append(position)
    return list(reversed(indices))


def _rank_original(sentences, spaces):
    rank = 0
    for sentence, space in zip(sentences, spaces):
        index = next((i for i, variant in enumerate(space.variants) if variant.text == sentence), None)
        if index is None:
            return None
        rank = rank * len(space.variants) + index
    return rank


def _surface_metrics(source, output):
    a, b = source.lower().split(), output.lower().split()
    left, right = set(a), set(b)
    # Lexical diagnostics only: negation/roles can change while overlap stays high.
    bigrams_a, bigrams_b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return {
        'token_set_jaccard': len(left & right) / len(left | right) if left | right else 1.0,
        'bigram_set_jaccard': len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b) if bigrams_a | bigrams_b else 1.0,
        'input_tokens': len(a), 'output_tokens': len(b),
        'interpretation': 'Surface overlap diagnostics; not meaning or watermark scores.',
    }


def paraphrase(text: str, *, candidates: int = 16, seed: int | None = None,
               backend: RewriteBackend | None = None, context=None,
               entailment_verifier=None) -> ParaphraseResult:
    """Return text plus auditable variability and structural fidelity reports.

    Defaults use OS-backed randomness. Seeded runs are for testing only. Long
    passages are handled sentence by sentence without the core Document limit;
    no unsupported sentence is silently copied into an otherwise rewritten text.
    """
    if type(candidates) is not int or not 1 <= candidates <= 256:
        raise ValueError('candidates must be an integer from 1 through 256')
    if seed is not None and type(seed) is not int:
        raise ValueError('seed must be an integer or None')
    from ..alternations import RewriteContext
    if context is not None and not isinstance(context, RewriteContext):
        raise ValueError('context must be RewriteContext or None')
    if entailment_verifier is not None and not callable(entailment_verifier):
        raise ValueError('entailment_verifier must be callable or None')
    backend = backend or SymbolicBackend()
    base_report = {
        'schema_version': 1, 'backend': backend.name,
        'surface_artifacts': inspect_surface(text),
        'selection': {'randomness': 'os_backed' if seed is None else 'seeded_test_only',
                      'candidate_budget': candidates,
                      'method': 'uniform_distinct_candidate_sample_then_uniform_selection'},
        'limitations': list(LIMITATIONS),
        'disruption_evaluation': {
            'watermark_detector_run': False,
            'source_attribution_test_run': False,
            'adaptive_channel_test_run': False,
            'covert_signal_removal_established': False,
        },
    }
    from ..alternations import inventory
    base_report['alternations'] = {'registered': 45, 'inventory': [
        {**item, 'status': 'not_matched', 'missing_context': []} for item in inventory()],
        'guard_context_source': 'trusted_caller_not_input_text'}
    # The symbolic backend is the coverage gate; no source text is included in reports.
    try:
        normalized = canonicalize(text)
    except ValueError as exc:
        base_report.update({'canonicalization': {'status': 'rejected', 'reason': str(exc)},
                            'coverage': {'complete': False},
                            'variability': None, 'meaning': None})
        return ParaphraseResult('unsupported', None, base_report)
    base_report['canonicalization'] = {
        'operations_applied': list(normalized.changes),
        'scope': 'NFKC and whitespace only; no homoglyph mapping, markdown rewriting, or code rewriting.',
        'fidelity_reference': 'normalized_input; normalization itself is not semantically verified',
    }
    if backend.name == 'controlled_english_symbolic_v1':
        from ..alternations.engine import rewrite_catalog
        catalog_result = rewrite_catalog(text, base_report=base_report, candidates=candidates,
                                         seed=seed, context=context, verifier=entailment_verifier)
        if catalog_result is None:
            from ..alternations.mixed import rewrite_mixed
            catalog_result = rewrite_mixed(text, base_report=base_report, candidates=candidates,
                                           seed=seed, context=context, verifier=entailment_verifier)
        if catalog_result is not None:
            status, output, report = catalog_result
            report['surface_change'] = _surface_metrics(normalized.text, output)
            return ParaphraseResult(status, output, report)
    try:
        sentences = split_sentences(normalized.text)
    except ValueError as exc:
        base_report.update({'coverage': {'complete': False, 'reason': str(exc)},
                            'variability': None, 'meaning': None})
        return ParaphraseResult('unsupported', None, base_report)
    if len(sentences) > 1000:
        raise ValueError('At most 1000 sentences per paraphrase request')
    spaces, failures = [], []
    for index, sentence in enumerate(sentences):
        try:
            spaces.append(backend.analyze(sentence))
        except ValueError as exc:
            failures.append({'sentence': index + 1, 'reason': str(exc)})
    base_report['coverage'] = {'complete': not failures, 'sentences': len(sentences),
                               'supported_sentences': len(spaces), 'failures': failures}
    if failures:
        base_report.update({'variability': None, 'meaning': None})
        return ParaphraseResult('unsupported', None, base_report)

    total = math.prod(len(space.variants) for space in spaces)
    original_rank = _rank_original(sentences, spaces)
    # Include the original wording: excluding it would condition the rewrite
    # distribution on a source-controlled lexical/structural choice.
    available = total
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)
    # Sample ranks instead of materializing the exponential passage-wide product.
    count = min(candidates, available)
    ranks = set()
    while len(ranks) < count:
        rank = rng.randrange(available)
        ranks.add(rank)
    sampled = sorted(ranks)
    chosen = rng.choice(sampled)
    positions = _unrank(chosen, spaces)
    output_sentences = [space.variants[i].text for space, i in zip(spaces, positions)]
    output = ' '.join(output_sentences)
    # Independent final gate: do not trust backend filtering alone.
    fidelity = []
    for source_sentence, sentence in zip(sentences, output_sentences):
        decoded = parse(sentence)
        if len(decoded.propositions) != 1:
            raise ValueError('Final fidelity gate rejected a changed proposition count')
        original = parse(source_sentence).propositions[0]
        fidelity.append(compare_meaning(original, decoded.propositions[0]))
    if not all(score.exact_match for score in fidelity):
        raise ValueError('Final structural fidelity gate rejected the selected rewrite')
    axes = [{'sentence': i + 1, 'parameter': name, 'values': list(values)}
            for i, space in enumerate(spaces) for name, values in space.parameters]
    base_report['selection']['candidates_sampled'] = count
    base_report['selection']['unchanged_rendering_excluded'] = False
    base_report['variability'] = {
        'choice_parameters': len(axes), 'parameters': axes,
        'variable_sentences': sum(len(space.variants) > 1 for space in spaces),
        'distinct_renderings': str(total),
        'alternative_renderings_to_input': str(total - (original_rank is not None)),
        'log2_distinct_renderings': math.log2(total),
        'per_sentence_renderings': [len(space.variants) for space in spaces],
        'rejected_sentence_candidates': sum(space.rejected_candidates for space in spaces),
        'count_scope': 'Exact product of deduplicated verified sentence renderings in this backend; not all English paraphrases.',
        'axes_are_independent': False,
    }
    # Existing realizers implement several catalog methods on a wider controlled
    # grammar; expose that applicability rather than reporting them not matched.
    core_methods = {'voice': 12, 'recipient_structure': 13,
                    'location_position': 30, 'information_request_form': 33}
    for axis in axes:
        method_id = core_methods.get(axis['parameter'])
        if method_id is not None:
            record = base_report['alternations']['inventory'][method_id - 1]
            record.update({'status': 'enabled', 'missing_context': [],
                           'provider': 'core_structural_realizer'})
            record.setdefault('sites', []).append({'sentence': axis['sentence'], 'values': axis['values']})
    base_report['meaning'] = {
        'method': 'structural_field_agreement',
        'score': sum(f.score for f in fidelity) / len(fidelity),
        'all_propositions_match': True,
        'matched_fields': sum(f.matched_fields for f in fidelity),
        'compared_fields': sum(f.compared_fields for f in fidelity),
        'sentence_scores': [asdict(f) for f in fidelity],
        'scope': 'Encoded meaning of normalized input; curated lexical equivalences assumed.',
        'general_semantic_similarity': None,
        'nli_evaluated': False,
    }
    base_report['surface_change'] = _surface_metrics(normalized.text, output)
    changed = output_sentences != sentences
    return ParaphraseResult('reworded' if changed else 'unchanged', output, base_report)
