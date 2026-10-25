import json
import unittest
from unittest.mock import Mock
from symbolnlp import RewriteContext, paraphrase
from symbolnlp.alternations import inventory
from symbolnlp.alternations.catalog import RULES
from symbolnlp.alternations.engine import ASSUMPTIONS

VALUES = {'owner': 'company', 'head': 'CEO', 'name': 'Ann', 'other': 'Tom',
          'color': 'red', 'noun': 'car', 'subject': 'we', 'object': 'the file',
          'item': 'cost', 'item2': 'speed', 'item3': 'quality', 'actor': 'we', 'transitive': 'help', 'plural': 'students', 'number': '3',
          'month': 'October', 'day': '25', 'year': '2026',
          'x': 'the test failed', 'y': 'we left', 'thing': 'file', 'verb': 'worked'}


class AlternationTests(unittest.TestCase):
    def test_all_45_have_real_executable_grammars(self):
        self.assertEqual([r.id for r in RULES], list(range(1, 46)))
        self.assertEqual(len(inventory()), 45)
        trusted = RewriteContext(ASSUMPTIONS)
        for rule in RULES:
            for family in (rule.forms,) + rule.additional_forms:
                source = family[0].template.format_map(VALUES)
                with self.subTest(method=rule.id, source=source):
                    slots = rule.decode(source)
                    self.assertIsNotNone(slots)
                    self.assertGreater(len(set(rule.outputs(slots))), 1)
                    for output in rule.outputs(slots):
                        self.assertIsNotNone(rule.decode(output))
                    result = paraphrase(source, context=trusted,
                                        entailment_verifier=lambda a, b: True, seed=3)
                    self.assertIsNotNone(result.text)
                    self.assertGreater(int(result.report['variability']['distinct_renderings']), 1)
                    record = result.report['alternations']['inventory'][rule.id - 1]
                    self.assertEqual(record['status'], 'enabled')
                    self.assertGreater(record['accepted_edges'], 0)
                    self.assertEqual(result.report['meaning']['method'], 'replayed_rule_derivation')
                    self.assertIsNone(result.report['meaning']['general_semantic_similarity'])
                    json.dumps(result.to_dict())

    def test_guards_are_not_silently_assumed(self):
        for rule in RULES:
            if rule.requires:
                source = rule.forms[0].template.format_map(VALUES)
                result = paraphrase(source, seed=7)
                record = result.report['alternations']['inventory'][rule.id - 1]
                self.assertEqual(record['status'], 'blocked', rule.id)
                self.assertTrue(record['missing_context'])
        result = paraphrase('She must leave.', context=RewriteContext({'ability_modal_reading'}))
        self.assertIn('deontic_modal_reading', result.report['alternations']['inventory'][17]['missing_context'])
        with self.assertRaises(ValueError):
            RewriteContext({'source_says_it_is_safe'})

    def test_entailment_required_in_both_directions(self):
        blocked = paraphrase('It is not uncommon.')
        self.assertEqual(blocked.report['variability']['distinct_renderings'], '1')
        reject = Mock(return_value=False)
        result = paraphrase('It is not uncommon.', entailment_verifier=reject)
        self.assertEqual(result.text, 'It is not uncommon.')
        self.assertGreaterEqual(reject.call_count, 2)
        partial = lambda a, b: a.startswith('It is not')
        self.assertEqual(paraphrase('It is not uncommon.', entailment_verifier=partial).report['variability']['distinct_renderings'], '1')
        accepted = paraphrase('It is not uncommon.', entailment_verifier=lambda a, b: True)
        self.assertEqual(accepted.report['variability']['distinct_renderings'], '2')
        self.assertTrue(accepted.report['meaning']['external_entailment_evaluated'])
        self.assertFalse(accepted.report['meaning']['nli_evaluated'])

    def test_unsafe_inputs_and_slot_changes_are_not_rules(self):
        for source in ['She stopped running.', 'She remembered to run.',
                       'She only finished the test.', 'The rule, which applies, is clear.',
                       'The meeting is on 10/99.', 'The meeting is on 25/10.',
                       'The test ran. She failed.', 'The company might resign.']:
            result = paraphrase(source)
            self.assertIsNone(result.text, source)
        r = RULES[19]
        a = r.decode('Ann precedes Tom.')
        b = r.decode('Tom follows Ann.')
        c = r.decode('Ann follows Tom.')
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_lists_and_discourse_counts_are_deduplicated(self):
        context = RewriteContext({'unordered_list'})
        result = paraphrase('- Cost\n- Speed\n- Quality', context=context, seed=2)
        self.assertEqual(result.report['variability']['distinct_renderings'], '18')
        self.assertEqual(result.report['variability']['choice_parameters'], 3)  # list prose, ordering, Oxford comma
        self.assertEqual(set(result.text.replace('- ', '').replace('and ', '').replace(',', '').replace('.', '').lower().split()), {'cost', 'speed', 'quality'})
        self.assertTrue(result.report['surface_artifacts']['detected'])

    def test_composition_with_core_questions(self):
        result = paraphrase('Turn off the light. Does Alice help Bob?', seed=2)
        self.assertEqual(result.report['backend'], 'mixed_bounded_grammar_v1')
        self.assertEqual(result.report['variability']['per_unit_renderings'], [2, 8])
        self.assertEqual(result.report['variability']['distinct_renderings'], '16')
        self.assertIn('?', result.text)
        self.assertEqual(result.report['meaning']['score'], 1)
        incomplete = paraphrase('Turn off the light. Something wholly unsupported follows here.')
        self.assertIsNone(incomplete.text)

    def test_spelling_is_document_wide(self):
        source = 'We analyze the color. They analyze the color. We analyze the color.'
        for seed in range(10):
            result = paraphrase(source, seed=seed)
            self.assertEqual(result.report['variability']['distinct_renderings'], '2')
            self.assertFalse('analyze' in result.text and 'analyse' in result.text)
            self.assertFalse('color' in result.text and 'colour' in result.text)

    def test_distribution_ignores_source_form(self):
        for seed in range(5):
            self.assertEqual(paraphrase('Turn off the light.', seed=seed).text,
                             paraphrase('Turn the light off.', seed=seed).text)
            self.assertEqual(paraphrase('The company\'s CEO resigned.', seed=seed).text,
                             paraphrase('The CEO of the company resigned.', seed=seed).text)


if __name__ == '__main__':
    unittest.main()
