import unittest
from symbolnlp import parse, paraphrase, compare_meaning
from symbolnlp.rewording.backend import SymbolicBackend


class RealizationTests(unittest.TestCase):
    def variants(self, text):
        space = SymbolicBackend().analyze(text)
        original = parse(text).propositions[0]
        for candidate in space.variants:
            decoded = parse(candidate.text).propositions[0]
            self.assertTrue(compare_meaning(original, decoded).exact_match, candidate.text)
        return {v.text for v in space.variants}

    def test_named_entities(self):
        short = 'What is the weather like in Chicago in October?'
        expanded = 'What is the weather like in the city of Chicago in October?'
        self.assertEqual(self.variants(short), {short, expanded})
        self.assertEqual(self.variants(short), self.variants(expanded))
        self.assertEqual(parse(short), parse(expanded))
        self.assertEqual(self.variants('What is Venus like?'),
                         {'What is Venus like?', 'What is the planet Venus like?'})
        self.assertEqual(parse('What is Venus like?'), parse('What is the planet Venus like?'))
        for text in ['Chicago helps Bob.', 'Venus is a planet.', 'Alice sees Venus.']:
            self.assertGreaterEqual(len(self.variants(text)), 2)
        # Never invent a type for an unregistered proper name.
        self.assertEqual(len(self.variants('What is Tom like?')), 1)

    def test_requests_and_modifier_senses(self):
        question = 'What are some great novels from 1900-1950?'
        expected = {prefix + 'some ' + adjective + ' novels from 1900-1950' + terminator
                    for prefix, terminator in [('What are ', '?'), ('Tell me ', '.'), ('Give me ', '.')]
                    for adjective in ['great', 'outstanding']}
        self.assertEqual(self.variants(question), expected)
        for text in expected:
            self.assertEqual(parse(text), parse(question))
            self.assertEqual(self.variants(text), expected)
        result = paraphrase(question, seed=3)
        self.assertEqual(result.report['variability']['choice_parameters'], 2)
        self.assertEqual(result.report['variability']['distinct_renderings'], '6')
        self.assertEqual(result.report['meaning']['score'], 1)
        self.assertIn(result.text, expected)

    def test_fidelity_does_not_drop_constraints(self):
        source = parse('What are some great novels from 1900-1950?').propositions[0]
        for text in ['Give me some great novels from 1950-1960.',
                     'Tell me some good novels from 1900-1950.',
                     'Tell me some great books from 1900-1950.']:
            self.assertFalse(compare_meaning(source, parse(text).propositions[0]).exact_match)
        # A transfer of physical objects is not generically normalized to a query.
        physical = parse('Give me some dogs.').propositions[0]
        self.assertEqual(physical.mood, 'imperative')
        self.assertEqual(physical.sense, 'give.v.01')
        self.assertIsNone(physical.question)

    def test_combined_count_and_distributions(self):
        passage = ('What is the weather like in Chicago in October? '
                   'What is the planet Venus like? '
                   'What are some great novels from 1900-1950?')
        result = paraphrase(passage, seed=7)
        self.assertEqual(result.report['variability']['per_sentence_renderings'], [2, 2, 6])
        self.assertEqual(result.report['variability']['distinct_renderings'], '24')
        self.assertEqual(result.report['variability']['choice_parameters'], 4)
        for seed in range(5):
            self.assertEqual(paraphrase('What is Venus like?', seed=seed).text,
                             paraphrase('What is the planet Venus like?', seed=seed).text)
            self.assertEqual(paraphrase('Tell me some outstanding novels from 1900-1950.', seed=seed).text,
                             paraphrase('What are some great novels from 1900-1950?', seed=seed).text)


if __name__ == '__main__':
    unittest.main()
