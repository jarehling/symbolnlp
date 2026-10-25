import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from symbolnlp import compare_meaning, paraphrase, parse
from symbolnlp.rewording.backend import SentenceSpace, SymbolicBackend, Variant
from symbolnlp.rewording.canonical import canonicalize


class RewordingTests(unittest.TestCase):
    def test_variation_count(self):
        result = paraphrase('Alice helps Bob.', seed=1)
        self.assertIn(result.status, {'reworded', 'unchanged'})
        v = result.report['variability']
        self.assertEqual(v['choice_parameters'], 2)
        self.assertEqual(v['distinct_renderings'], '8')
        self.assertEqual(v['alternative_renderings_to_input'], '7')
        self.assertEqual(v['log2_distinct_renderings'], 3)
        self.assertEqual(result.report['meaning']['score'], 1)
        self.assertIsNone(result.report['meaning']['general_semantic_similarity'])
        self.assertTrue(result.report['coverage']['complete'])

    def test_long_passage_product_without_materializing(self):
        result = paraphrase(' '.join(['Alice helps Bob.'] * 50), seed=7)
        self.assertEqual(result.report['coverage']['sentences'], 50)
        self.assertEqual(result.report['variability']['distinct_renderings'], str(8 ** 50))
        self.assertEqual(result.report['variability']['choice_parameters'], 100)
        self.assertEqual(result.report['variability']['log2_distinct_renderings'], 150)
        self.assertEqual(len(result.text.split('.')) - 1, 50)
        self.assertEqual(result.report['selection']['candidates_sampled'], 16)

    def test_structural_choices_and_dependencies(self):
        result = paraphrase('Alice helps Bob. On the building, a bird sat. Give me the butter.', seed=4)
        self.assertEqual(result.report['variability']['per_sentence_renderings'], [8, 2, 2])
        self.assertEqual(result.report['variability']['distinct_renderings'], '32')
        # Active to, active double object, and patient-passive to: not 2*2 choices.
        result = paraphrase('Alice gives me the butter.', seed=1)
        self.assertEqual(result.report['variability']['distinct_renderings'], '3')
        self.assertFalse(result.report['variability']['axes_are_independent'])

    def test_every_variant_is_equivalent(self):
        examples = ['Alice helps Bob.', 'I help him.', 'Rice was cooked in the steamer.',
                    'On the building, a bird sat.', 'Give me the butter.',
                    'Alice gave him the butter in the school.', 'I am a friend of Tom.',
                    'Glory is pleasing to the proud.', 'It is 90 degrees outside.',
                    'Rice was given to me by Tom.', 'Do not give her rice.',
                    'Tom will not help me on the building.', 'At the school, I helped Tom.']
        for text in examples:
            with self.subTest(text=text):
                space = SymbolicBackend().analyze(text)
                self.assertEqual(len({v.text for v in space.variants}), len(space.variants))
                for variant in space.variants:
                    self.assertTrue(compare_meaning(space.source, parse(variant.text).propositions[0]).exact_match)

    def test_low_variability_is_honest(self):
        result = paraphrase('It is 90 degrees outside.', seed=2)
        self.assertEqual(result.status, 'unchanged')
        self.assertEqual(result.text, 'It is 90 degrees outside.')
        self.assertEqual(result.report['variability']['choice_parameters'], 0)
        self.assertEqual(result.report['variability']['distinct_renderings'], '1')
        self.assertEqual(result.report['variability']['alternative_renderings_to_input'], '0')
        self.assertEqual(result.report['variability']['log2_distinct_renderings'], 0)

    def test_fail_closed_on_partial_coverage(self):
        result = paraphrase('Alice helps Bob. Quantum mechanics is weird.', seed=1)
        self.assertIsNone(result.text)
        self.assertEqual(result.status, 'unsupported')
        self.assertEqual(result.report['coverage']['supported_sentences'], 1)
        self.assertIsNone(result.report['meaning'])
        self.assertIsNone(result.report['variability'])
        self.assertEqual(result.report['coverage']['failures'][0]['sentence'], 2)
        for text in ['Alice helps Bob..', '```python\nprint(1)\n```', '# Alice helps Bob.']:
            self.assertEqual(paraphrase(text).status, 'unsupported')

    def test_meaning_metric_catches_critical_changes(self):
        source = parse('Alice helps Bob.').propositions[0]
        for text, field in [('Bob helps Alice.', 'agent'), ('Alice does not help Bob.', 'negated'),
                            ('Alice helped Bob.', 'tense'), ('Alice can help Bob.', 'modal'),
                            ('Alice likes Bob.', 'sense')]:
            score = compare_meaning(source, parse(text).propositions[0])
            self.assertFalse(score.exact_match)
            self.assertLess(score.score, 1)
            self.assertIn(field, score.differing_fields)
        for a, b in [('Two dogs chase that cat.', 'Three dogs chase that cat.'),
                     ('The dog chases the cat.', 'A dog chases the cat.'),
                     ('It is 90 degrees outside.', 'It is 80 degrees outside.'),
                     ('I give rice to him.', 'I give rice to her.')]:
            self.assertFalse(compare_meaning(parse(a).propositions[0], parse(b).propositions[0]).exact_match)

    def test_final_gate_is_independent_of_backend(self):
        class BadBackend:
            name = 'test_bad_backend'
            def analyze(self, sentence):
                changed = parse('Bob helps Alice.').propositions[0]
                return SentenceSpace(changed, (Variant('Bob helps Alice.', ()),), 0, ())
        with self.assertRaisesRegex(ValueError, 'fidelity gate'):
            paraphrase('Alice helps Bob.', backend=BadBackend())
        class ExtraBackend:
            name = 'test_extra_backend'
            def analyze(self, sentence):
                source = parse(sentence).propositions[0]
                return SentenceSpace(source, (Variant('Alice helps Bob. Bob helps Alice.', ()),), 0, ())
        with self.assertRaisesRegex(ValueError, 'proposition count'):
            paraphrase('Alice helps Bob.', backend=ExtraBackend())

    def test_canonicalization(self):
        canonical = canonicalize('Ａlice\t helps\nBob.')
        self.assertEqual(canonical.text, 'Alice helps Bob.')
        self.assertEqual(canonical.changes, ('unicode_nfkc', 'whitespace'))
        self.assertEqual(paraphrase('Alice\u200b helps Bob.').status, 'unsupported')
        result = paraphrase('Ａlice\t helps\nBob.', seed=1)
        self.assertEqual(result.report['canonicalization']['operations_applied'], ['unicode_nfkc', 'whitespace'])

    def test_randomness(self):
        self.assertEqual(paraphrase('Alice helps Bob.', seed=7), paraphrase('Alice helps Bob.', seed=7))
        outputs = {paraphrase('Alice helps Bob.', seed=seed).text for seed in range(100)}
        self.assertEqual(len(outputs), 8)
        with patch('symbolnlp.rewording.pipeline.secrets.SystemRandom', wraps=__import__('secrets').SystemRandom) as secure:
            result = paraphrase('Alice helps Bob.')
            secure.assert_called_once()
        self.assertEqual(result.report['selection']['randomness'], 'os_backed')

    def test_cli(self):
        run = subprocess.run([sys.executable, '-m', 'symbolnlp', 'paraphrase',
                              'Alice helps Bob.', '--seed', '3'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)['status'], 'reworded')
        run = subprocess.run([sys.executable, '-m', 'symbolnlp', 'paraphrase', '--text-only', '--seed', '3'],
                             input='Alice helps Bob.', capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertNotIn('report', run.stdout)
        self.assertTrue(run.stdout.endswith('.\n'))
        run = subprocess.run([sys.executable, '-m', 'symbolnlp', 'paraphrase', 'unsupported text'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(json.loads(run.stdout)['text'])

    def test_same_meaning_same_variant_distribution(self):
        active = SymbolicBackend().analyze('Alice helps Bob.')
        passive = SymbolicBackend().analyze('Bob is assisted by Alice.')
        self.assertEqual([v.text for v in active.variants], [v.text for v in passive.variants])
        for seed in range(10):
            self.assertEqual(paraphrase('Alice helps Bob.', seed=seed).text,
                             paraphrase('Bob is assisted by Alice.', seed=seed).text)
        self.assertFalse(paraphrase('Alice helps Bob.').report['selection']['unchanged_rendering_excluded'])
        self.assertEqual([v.text for v in SymbolicBackend().analyze('2 dogs chased the cat.').variants],
                         [v.text for v in SymbolicBackend().analyze('Two dogs chased the cat.').variants])

    def test_evaluation(self):
        from symbolnlp.rewording.evaluation import evaluate
        result = evaluate(['Alice helps Bob.', 'It is 90 degrees outside.', 'Unknown sentence.'], trials=64)
        varied, fixed, unsupported = result['records']
        self.assertEqual(varied['structural_fidelity_passes'], 64)
        self.assertEqual(varied['unique_outputs'], 8)
        self.assertGreater(varied['empirical_output_entropy_bits'], 2)
        self.assertEqual(fixed['unique_outputs'], 1)
        self.assertEqual(fixed['empirical_output_entropy_bits'], 0)
        self.assertEqual(unsupported['status'], 'unsupported')
        self.assertIsNone(unsupported['empirical_output_entropy_bits'])
        self.assertIsNone(varied['detector'])
        probed = evaluate(['Alice helps Bob.'], trials=4, detector=lambda text: float(len(text)))
        self.assertIsNotNone(probed['records'][0]['detector'])
        self.assertFalse(probed['watermark_disruption_established'])

    def test_invalid_configuration(self):
        for count in [0, 257, True]:
            with self.assertRaises(ValueError):
                paraphrase('Alice helps Bob.', candidates=count)
        with self.assertRaises(ValueError):
            SymbolicBackend().analyze('Alice helps Bob. Bob helps Alice.')


if __name__ == '__main__':
    unittest.main()
