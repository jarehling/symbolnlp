import unittest
from symbolnlp import Document, Entity, Measurement, Proposition, parse, render
from symbolnlp.core import INTRANSITIVE


class PredicateTests(unittest.TestCase):
    def roundtrip(self, text):
        doc = parse(text)
        self.assertEqual(Document.from_dict(doc.to_dict()), doc)
        for voice in ['active', 'passive', 'random']:
            self.assertEqual(parse(render(doc, structure=voice, seed=4)), doc)
        return doc.propositions[0]

    def test_requested_examples(self):
        event = self.roundtrip('On the building, a bird sat.')
        self.assertEqual(event.sense, 'sit.v.01')
        self.assertEqual(event.agent.noun, 'bird')
        self.assertIsNone(event.patient)
        self.assertEqual(event.tense, 'past')
        self.assertEqual(event.adjuncts[0].preposition, 'on')
        self.assertEqual(event.adjuncts[0].entity.noun, 'building')
        adjective = self.roundtrip('Glory is pleasing to the proud.')
        self.assertEqual(adjective.sense, 'pleasing.a.01')
        self.assertEqual(adjective.subject.noun, 'glory')
        self.assertTrue(adjective.subject.mass)
        self.assertEqual(adjective.experiencer.nominalized_adjective, 'proud')
        self.assertEqual(adjective.experiencer.number, 'plural')
        weather = self.roundtrip('It is 90 degrees outside.')
        self.assertEqual(weather.sense, 'temperature.n.01')
        self.assertIsNone(weather.subject)
        self.assertEqual(weather.measurement.value, 90)
        self.assertIsNone(weather.measurement.scale)
        self.assertEqual(weather.location_adverb, 'outside')

    def test_intransitive_inflections(self):
        for sense, variants in INTRANSITIVE.items():
            for base, third, past, _ in variants:
                for subject, present, do in [('I', base, 'do'), ('the bird', third, 'does'),
                                             ('the birds', base, 'do')]:
                    for phrase in [present, past, f'{do} not {base}', f'did not {base}',
                                   f'will {base}', f'can {base}', f'will not {base}']:
                        p = self.roundtrip(f'{subject} {phrase} on the building.')
                        self.assertEqual(p.sense, sense)
                self.roundtrip(f'{base.capitalize()} outside.')
                self.roundtrip(f'Do not {base} on the building.')
        self.assertEqual(parse('On the building, a bird sat.'), parse('A bird sat on the building.'))
        self.roundtrip('At the school, Tom helped me.')

    def test_adjectival_predicates_and_abstracts(self):
        for text in ['Glory was pleasing to him.', 'Pride is not pleasing to the poor.',
                     'Knowledge may be pleasing to the young.', 'The proud are happy.',
                     'She is proud.', 'I am happy outside.', 'The rich were not happy.',
                     'Happiness helps him.', 'I like glory.', 'Glory is a friend of Tom.']:
            self.roundtrip(text)

    def test_temperatures(self):
        for text in ['It was -5 degrees Celsius outside.', 'It is 1 degree Fahrenheit inside.',
                     'It will be 30 degrees.', 'It may not be 90 degrees outside.',
                     'It is 0 degrees outdoors.', 'It was not 20 degrees indoors.']:
            self.roundtrip(text)

    def test_without_surface_text(self):
        for text, expected in [
            ('On the building, a bird sat.', 'A bird sat on the building.'),
            ('Glory is pleasing to the proud.', 'Glory is pleasing to the proud.'),
            ('It is 90 degrees outside.', 'It is 90 degrees outside.'),
        ]:
            data = parse(text).to_dict()
            def strip_text(value):
                if isinstance(value, dict):
                    if 'text' in value:
                        value['text'] = None
                    for child in value.values():
                        strip_text(child)
                elif isinstance(value, (list, tuple)):
                    for child in value:
                        strip_text(child)
            strip_text(data)
            self.assertEqual(render(Document.from_dict(data)), expected)
        weather = Document((Proposition('temperature.n.01', measurement=Measurement(90),
                                          location_adverb='outside'),))
        self.assertEqual(render(weather), 'It is 90 degrees outside.')

    def test_invalid(self):
        for text in ['A bird sat the cat.', 'A bird was sat by Tom.',
                     'On the building, a bird sat, outside.', 'The bird, sat.',
                     'On, a bird sat.', 'A bird sit.', 'Glory are pleasing to him.',
                     'Glory is pleasing to.', 'Glory is happy to him.',
                     'The proud is happy.', 'It are 90 degrees outside.',
                     'He is 90 degrees outside.', 'It is 1 degrees outside.',
                     'It is 90 degree outside.', 'It is 90 degrees Kelvin outside.']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)
        with self.assertRaises(ValueError):
            Entity(nominalized_adjective='proud')
        with self.assertRaises(ValueError):
            Proposition('sit.v.01', agent=Entity(noun='bird'), patient=Entity(noun='cat'))
        with self.assertRaises(ValueError):
            Measurement(True)


if __name__ == '__main__':
    unittest.main()
