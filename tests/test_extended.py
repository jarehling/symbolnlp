import unittest
from symbolnlp import Adjunct, Document, Entity, Proposition, UnsupportedText, parse, render


class ExtendedTests(unittest.TestCase):
    def check_roundtrip(self, text):
        doc = parse(text)
        self.assertEqual(Document.from_dict(doc.to_dict()), doc)
        for structure in ['active', 'passive', 'random']:
            with self.subTest(text=text, structure=structure):
                self.assertEqual(parse(render(doc, structure=structure, seed=3)), doc)
        return doc.propositions[0]

    def test_requested_sentences(self):
        relation = self.check_roundtrip('I am a friend of Tom.')
        self.assertEqual(relation.sense, 'friend.n.01')
        self.assertEqual(relation.subject.pronoun, 'i')
        self.assertEqual(relation.related_to.text, 'Tom')
        self.assertIsNone(relation.agent)
        command = self.check_roundtrip('Give me the butter.')
        self.assertEqual(command.sense, 'give.v.01')
        self.assertEqual(command.mood, 'imperative')
        self.assertEqual(command.agent.pronoun, 'you')
        self.assertEqual(command.recipient.pronoun, 'i')
        self.assertEqual(command.patient.noun, 'butter')
        self.assertTrue(command.patient.mass)
        cooking = self.check_roundtrip('Rice was cooked in the steamer.')
        self.assertEqual(cooking.sense, 'cook.v.01')
        self.assertEqual(cooking.tense, 'past')
        self.assertIsNone(cooking.agent)
        self.assertTrue(cooking.patient.mass)
        self.assertEqual(cooking.adjuncts[0].preposition, 'in')
        self.assertEqual(cooking.adjuncts[0].entity.noun, 'steamer')

    def test_pronouns(self):
        for text in ['I help him.', 'You help me.', 'She helps us.', 'We help them.',
                     'They helped her.', 'I am helped by you.', 'You were helped by me.',
                     'She does not help him.', 'We do not help them.']:
            self.check_roundtrip(text)
        self.assertEqual(render(parse('I help him.'), structure='passive'), 'He is helped by me.')
        self.assertEqual(render(parse('She helps us.'), structure='passive'), 'We are helped by her.')

    def test_copulas(self):
        for text in ['I was not a friend of him.', 'She is a neighbor of Tom.',
                     'You are the friend of her.', 'I will be a friend of Tom.',
                     'She might not be a friend of him.', 'I am a friend.',
                     'Tom is a teacher.', 'They are teachers.', 'She was not a teacher.',
                     'You should be a teacher.', 'I will not be a teacher.']:
            self.check_roundtrip(text)

    def test_giving_and_commands(self):
        for text in ['Give me the butter.', 'Give the butter to me.', 'Give Tom rice.',
                     'Do not give her the butter.', 'Help him.', 'Cook rice in the steamer.',
                     'She gave him the butter.', 'I give the butter to her.',
                     'The butter was given to me by Tom.', 'The butter was given to me.']:
            self.check_roundtrip(text)
        self.assertEqual(parse('Give me the butter.'), parse('Give the butter to me.'))
        self.assertEqual(render(parse('Give me the butter.')), 'Give the butter to me.')
        self.assertNotEqual(parse('You give me the butter.'), parse('Give me the butter.'))

    def test_locations_and_agentless(self):
        for text in ['Rice was cooked.', 'Rice was not cooked in the steamer.',
                     'Rice will be cooked in the steamer.', 'Rice can be cooked in the steamer.',
                     'Tom cooked rice in the steamer.', 'Tom cooked rice on the stove at the school.',
                     'Rice was cooked by him in the steamer.', 'Dogs are helped.']:
            self.check_roundtrip(text)

    def test_concept_only(self):
        rice = Entity(noun='rice', mass=True)
        steamer = Entity(noun='steamer', determiner='the')
        cooking = Document((Proposition('cook.v.01', patient=rice, tense='past',
                                        adjuncts=(Adjunct('in', steamer),)),))
        self.assertEqual(render(cooking), 'Rice was cooked in the steamer.')
        command = Document((Proposition('give.v.01', agent=Entity(pronoun='you'),
                            patient=Entity(noun='butter', mass=True, determiner='the'),
                            recipient=Entity(pronoun='i'), mood='imperative'),))
        self.assertEqual(render(command), 'Give the butter to me.')
        relation = Document((Proposition('friend.n.01', subject=Entity(pronoun='i'),
                                          related_to=Entity(text='Tom')),))
        self.assertEqual(render(relation), 'I am a friend of Tom.')

    def test_reject_malformed(self):
        for text in ['Me help Tom.', 'Tom helps I.', 'I is a friend of Tom.',
                     'I am a friend of.', 'Gave me the butter.',
                     'Rice were cooked in the steamer.', 'Two rice were cooked.', 'Rice was cooked in.',
                     'Tom cooked rice with the steamer.', 'I am a friend of Tom and Bob.']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)
        for fields in [dict(noun='rice', mass=True, quantity=1),
                       dict(noun='rice', mass=True, determiner='a'),
                       dict(pronoun='we'), dict(pronoun='me')]:
            with self.assertRaises(ValueError):
                Entity(**fields)


if __name__ == '__main__':
    unittest.main()
