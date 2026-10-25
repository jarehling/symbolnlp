import json
import unittest
from symbolnlp import paraphrase
from symbolnlp.rewording import inspect_surface


def kinds(report):
    return {item['kind'] for item in report['findings']}


class ArtifactTests(unittest.TestCase):
    def test_ordinary_sentence(self):
        report = inspect_surface('Alice helps Bob.')
        self.assertFalse(report['detected'])
        self.assertEqual(report['findings'], [])

    def test_homoglyphs_and_compatibility(self):
        report = inspect_surface('Аlice helps Bob. Ａlice helps Bob.')  # Cyrillic A; fullwidth A
        self.assertIn('possible_homoglyph', kinds(report))
        self.assertIn('mixed_script_word', kinds(report))
        self.assertIn('compatibility_character', kinds(report))
        first = next(f for f in report['findings'] if f['kind'] == 'possible_homoglyph')
        self.assertEqual(first['details']['codepoint'], 'U+0410')
        self.assertEqual(first['details']['latin_candidate'], 'A')
        self.assertEqual(first['positions'][0], {'offset': 0, 'length': 1, 'line': 1, 'column': 1})
        self.assertIn('possible_homoglyph', kinds(inspect_surface('Αlice')))  # Greek A
        # Legitimate Greek is still an observation, never a maliciousness verdict.
        self.assertIn('interpretation', report)

    def test_invisible_before_rejection(self):
        result = paraphrase('Alice\u200b helps Bob.\u202e')
        self.assertEqual(result.status, 'unsupported')
        report = result.report['surface_artifacts']
        self.assertIn('zero_width_or_variation_character', kinds(report))
        self.assertIn('bidirectional_control', kinds(report))
        self.assertIn('control_or_format_character', kinds(report))
        self.assertEqual(report['reference'], 'original_input_before_normalization')
        self.assertIn('zero_width_or_variation_character', kinds(inspect_surface('x\ufe0f')))

    def test_whitespace(self):
        text = '\tAlice  helps\u00a0Bob.  \r\n\n\nNext.\n'
        report = inspect_surface(text)
        self.assertTrue({'tab', 'repeated_spaces', 'nonstandard_whitespace',
                         'trailing_line_whitespace', 'repeated_blank_lines',
                         'leading_line_whitespace', 'mixed_line_endings'} <= kinds(report))
        self.assertEqual(report['line_ending_counts'], {'\\r\\n': 1, '\\n': 3})
        result = paraphrase('Alice  helps\tBob.', seed=2)
        self.assertIsNotNone(result.text)
        self.assertIn('tab', kinds(result.report['surface_artifacts']))
        self.assertEqual(result.report['canonicalization']['operations_applied'], ['whitespace'])

    def test_punctuation_and_caps(self):
        report = inspect_surface('alice said “HELLO”!!!  Bob.iPhone helps NASA .')
        self.assertTrue({'lowercase_sentence_initial', 'typographic_variant',
                         'all_caps_word', 'internal_capitals', 'repeated_punctuation',
                         'space_before_punctuation', 'missing_space_after_punctuation'} <= kinds(report))
        report = inspect_surface('one. two.')
        lower = next(f for f in report['findings'] if f['kind'] == 'lowercase_sentence_initial')
        self.assertEqual([p['offset'] for p in lower['positions']], [0, 5])

    def test_markdown_and_unsupported_passage(self):
        text = '# Heading\n- **one**  \n* two\n1. three\n> quote\n```py\n`x`\n```\n[a](b)'
        result = paraphrase(text)
        self.assertEqual(result.status, 'unsupported')
        report = result.report['surface_artifacts']
        self.assertTrue({'heading', 'bullet_marker', 'mixed_bullet_markers', 'ordered_list_marker',
                         'blockquote_marker', 'fence_marker', 'inline_code_marker',
                         'emphasis_marker', 'hard_line_break', 'link_or_image'} <= kinds(report))
        # Full source excerpts or invisibles are not echoed into audit fields.
        self.assertNotIn(text, json.dumps(report))

    def test_positions_and_bounded_reporting(self):
        report = inspect_surface('😀\n\tNASA NASA NASA', max_positions=2)
        tabs = next(f for f in report['findings'] if f['kind'] == 'tab')
        self.assertEqual(tabs['positions'][0], {'offset': 2, 'length': 1, 'line': 2, 'column': 1})
        caps = next(f for f in report['findings'] if f['kind'] == 'all_caps_word')
        self.assertEqual(caps['count'], 3)
        self.assertEqual(caps['positions_omitted'], 1)
        report = inspect_surface('\tА\u200b', max_groups=1)
        self.assertEqual(len(report['findings']), 1)
        self.assertGreater(report['omitted_group_occurrences'], 0)

    def test_no_rewrite_side_effects_and_every_failure_path(self):
        fullwidth = 'Ａlice helps Bob.'
        result = paraphrase(fullwidth, seed=1)
        self.assertIsNotNone(result.text)
        self.assertIn('compatibility_character', kinds(result.report['surface_artifacts']))
        for text in ['', '  ', 'Alice helps Bob..']:
            self.assertIn('surface_artifacts', paraphrase(text).report)
        for value in [None, 1]:
            with self.assertRaises(ValueError):
                inspect_surface(value)
        with self.assertRaises(ValueError):
            inspect_surface('text', max_positions=0)


if __name__ == '__main__':
    unittest.main()
