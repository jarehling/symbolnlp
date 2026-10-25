import unittest
from symbolnlp import Document, Entity, Proposition, UnsupportedText, parse, render, render_entity
from symbolnlp.core import LEXICON


class CoreTests(unittest.TestCase):
    def test_normalization(self):
        for word in ['helps', 'assists', 'aids', 'supports']:
            self.assertEqual(parse(f'Alice {word} Bob.'), parse('Alice helps Bob.'))

    def test_preserve(self):
        self.assertEqual(render(parse('Alice assisted Bob.', normalize=False),
                                vocabulary='preserve'), 'Alice assisted Bob.')

    def test_roles(self):
        self.assertEqual(parse('Alice helps Bob.'), parse('Bob is helped by Alice.'))
        self.assertNotEqual(parse('Alice helps Bob.'), parse('Bob helps Alice.'))

    def test_roundtrips(self):
        # Every lexical variant, tense, polarity, number and available voice.
        for sense, variants in LEXICON.items():
            for base, third, past, participle in variants:
                for subject, present, do in [('Alice', third, 'does'), ('the teachers', base, 'do')]:
                    for phrase in [present, past, f'{do} not {base}', f'did not {base}',
                                   f'will {base}', f'will not {base}', f'can {base}', f'must not {base}']:
                        doc = parse(f'{subject} {phrase} the student.')
                        self.assertEqual(doc.propositions[0].sense, sense)
                        for voice in ['active', 'passive', 'random']:
                            for vocab in ['canonical', 'random']:
                                with self.subTest(subject=subject, phrase=phrase, voice=voice, vocab=vocab):
                                    self.assertEqual(parse(render(doc, structure=voice, vocabulary=vocab, seed=7)), doc)

    def test_random(self):
        doc = parse('Alice helps Bob.')
        outputs = {render(doc, vocabulary='random', structure='random', seed=s) for s in range(50)}
        self.assertGreater(len(outputs), 4)
        self.assertEqual(render(doc, seed=2), render(doc, seed=2))

    def test_serialization(self):
        doc = parse('Alice helps Bob. Bob saw the dog. The dog follows Alice.')
        self.assertEqual(Document.from_dict(doc.to_dict()), doc)

    def test_requested_chase_sentences(self):
        examples = [
            ('Dogs chase cats.', 'present', 'dogs', 'cats', None, None),
            ('The dog chased the cat.', 'past', 'the dog', 'the cat', None, 'the'),
            ('The cat was chased by a dog.', 'past', 'a dog', 'the cat', None, 'the'),
            ('Two dogs chased that cat.', 'past', 'two dogs', 'that cat', 2, 'that'),
        ]
        for text, tense, agent, patient, quantity, determiner in examples:
            with self.subTest(text=text):
                doc = parse(text)
                p = doc.propositions[0]
                self.assertEqual(p.sense, 'chase.v.01')
                self.assertEqual((p.tense, p.agent.text, p.patient.text), (tense, agent, patient))
                self.assertEqual(p.agent.noun, 'dog')
                self.assertEqual(p.patient.noun, 'cat')
                self.assertEqual(p.agent.quantity, quantity)
                self.assertEqual(p.patient.determiner, determiner)
                self.assertEqual(Document.from_dict(doc.to_dict()), doc)
                for voice in ['active', 'passive', 'random']:
                    self.assertEqual(parse(render(doc, structure=voice, seed=9)), doc)

    def test_determiners_and_counts(self):
        for phrase in ['this dog', 'that dog', 'these dogs', 'those dogs',
                       'one dog', 'two dogs', 'zero dogs', 'ten dogs', '12 dogs', '1 dog']:
            doc = parse(f'Alice chased {phrase}.')
            self.assertEqual(parse(render(doc, structure='passive')), doc)
        self.assertEqual(parse('Dogs chase cats.').propositions[0].agent.number, 'plural')
        self.assertEqual(parse('12 dogs chase cats.').propositions[0].agent.quantity, 12)
        self.assertEqual(render(parse('Two dogs chased that cat.'), structure='passive'),
                         'That cat was chased by two dogs.')
        self.assertEqual(parse('A dog chased the cat.'), parse('The cat was chased by a dog.'))
        self.assertNotEqual(parse('The dog chased the cat.'), parse('The cat was chased by a dog.'))

    def test_invalid_new_noun_phrases(self):
        for text in ['Two dog chased that cat.', 'One dogs chase cats.',
                     'This dogs chase cats.', 'Those dog chased cats.',
                     'Dogs chases cats.', 'Cats was chased by dogs.',
                     'The dog that chased cats helps Bob.', 'Two two chase cats.']:
            with self.subTest(text=text), self.assertRaises(UnsupportedText):
                parse(text)

    def test_concept_only_generation(self):
        data = {"propositions": [{
            "sense": "chase.v.01",
            "agent": {"noun": "dog", "number": "singular"},
            "patient": {"noun": "cat", "number": "plural", "quantity": 2},
            "tense": "present",
        }]}
        doc = Document.from_dict(data)
        self.assertIsNone(doc.propositions[0].agent.text)
        self.assertEqual(render(doc), 'A dog chases two cats.')
        self.assertEqual(render(doc, structure='passive'), 'Two cats are chased by a dog.')
        self.assertEqual(Document.from_dict(doc.to_dict()), doc)
        decoded = parse(render(doc)).propositions[0]
        self.assertEqual(decoded.agent.noun, 'dog')
        self.assertEqual(decoded.patient.quantity, 2)
        self.assertEqual(decoded.patient.number, 'plural')

    def test_noun_phrase_construction(self):
        cases = [
            (Entity(noun='dog'), 'a dog'),
            (Entity(noun='animal'), 'an animal'),
            (Entity(noun='dog', number='plural'), 'dogs'),
            (Entity(noun='cat', determiner='the'), 'the cat'),
            (Entity(noun='cat', determiner='that'), 'that cat'),
            (Entity(noun='cat', number='plural', determiner='those'), 'those cats'),
            (Entity(noun='dog', quantity=1), 'one dog'),
            (Entity(noun='dog', number='plural', quantity=0), 'zero dogs'),
            (Entity(noun='dog', number='plural', quantity=12), '12 dogs'),
            (Entity(text='Alice'), 'Alice'),
            (Entity(text='2 cats', noun='cat', number='plural', quantity=2), '2 cats'),
        ]
        for entity, expected in cases:
            with self.subTest(entity=entity):
                self.assertEqual(render_entity(entity), expected)

    def test_concept_generation_agreement(self):
        for number, expected in [('singular', 'A dog chases cats.'),
                                 ('plural', 'Dogs chase cats.')]:
            doc = Document((Proposition('chase.v.01', Entity(noun='dog', number=number),
                                        Entity(noun='cat', number='plural')),))
            self.assertEqual(render(doc), expected)
            for voice in ['active', 'passive']:
                self.assertEqual(parse(render(doc, structure=voice)).propositions[0].agent.number, number)

    def test_invalid_entity_features(self):
        for features in [{}, {'noun': ''}, {'noun': 'two cats'}, {'text': ''},
                         {'noun': 'cat', 'number': 'plural', 'determiner': 'that'},
                         {'noun': 'cat', 'determiner': 'these'},
                         {'noun': 'cat', 'quantity': 2},
                         {'noun': 'cat', 'quantity': True},
                         {'noun': 'cat', 'quantity': 1, 'determiner': 'the'}]:
            with self.subTest(features=features), self.assertRaises(ValueError):
                Entity(**features)

    def test_reject(self):
        for text in ['', 'Alice helps Bob?', 'Alice helps Bob and Carol.',
                     'Alice thinks Bob helps Carol.',
                     'Alice help Bob.', 'Bob are helped by Alice.',
                     'Alice does helped Bob.', 'Alice helps Bob. ' * 4]:
            with self.subTest(text=text), self.assertRaises(UnsupportedText):
                parse(text)


if __name__ == '__main__':
    unittest.main()
