"""Offline variation/utility diagnostics and optional external detector hooks.

A detector callback must supply its own interpretation/validation. This module
never invents watermark, attribution, or covert-channel success scores.
"""
from collections import Counter
import math
from typing import Callable
from .pipeline import paraphrase


def evaluate(texts: list[str], *, trials: int = 32, seed: int = 0,
             detector: Callable[[str], float] | None = None) -> dict:
    """Reproducible evaluation, distinct from private production sampling."""
    if type(trials) is not int or not 1 <= trials <= 10000:
        raise ValueError('trials must be from 1 through 10000')
    records = []
    for text in texts:
        results = [paraphrase(text, seed=seed + i) for i in range(trials)]
        outputs = [result.text for result in results if result.text is not None]
        counts = Counter(outputs)
        n = len(outputs)
        entropy = -sum((count / n) * math.log2(count / n) for count in counts.values()) if n else None
        record = {
            'status': 'supported' if n == trials else 'unsupported',
            'trials': trials, 'successful_trials': n, 'unique_outputs': len(counts),
            'empirical_output_entropy_bits': entropy,
            'unchanged_trials': sum(result.status == 'unchanged' for result in results),
            'structural_fidelity_passes': sum(result.report.get('meaning', {}).get('all_propositions_match', False)
                                             for result in results if result.report.get('meaning')),
            'variability': results[0].report['variability'],
            'detector': None,
        }
        if detector is not None and outputs:
            original_score = float(detector(text))
            scores = [float(detector(output)) for output in outputs]
            if not all(math.isfinite(score) for score in [original_score, *scores]):
                raise ValueError('Detector scores must be finite')
            record['detector'] = {
                'original_score': original_score,
                'mean_output_score': sum(scores) / n,
                'mean_score_change': sum(scores) / n - original_score,
                'interpretation': 'User-supplied detector scores; direction and calibration are external.',
            }
        records.append(record)
    return {'mode': 'seeded_offline_evaluation', 'records': records,
            'watermark_disruption_established': False,
            'note': 'Output diversity and structural utility are diagnostics, not an adversarial channel-capacity or attribution evaluation.'}
