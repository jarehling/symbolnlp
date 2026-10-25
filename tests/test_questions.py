import json
import unittest
from symbolnlp import Document, Entity, Proposition, Question, QueryContext, compare_meaning, parse, paraphrase, render


class QuestionTests(unittest.TestCase):
    def roundtrip(self, text):
        doc = parse(text)
        self.assertEqual(Document.from_dict(json.loads(json.dumps(doc.to_dict()))), doc)
        for voice in ['active', 'passive', 'random']:
            with self.subTest(text=text, voice=voice):
                out = render(doc, structure=voice, seed=2)
                self.assertTrue(out.endswith('?'))
                self.assertEqual(parse(out), doc)
        result = paraphrase(text, seed=3)
        self.assertIsNotNone(result.text)
        self.assertEqual(result.report['meaning']['score'], 1)
        return doc.propositions[0]

    def test_requested_questions(self):
        p = self.roundtrip('What is the weather like in Chicago in October?')
        self.assertEqual(p.question.target, 'description')
        self.assertEqual(p.subject.noun, 'weather')
        self.assertEqual([(c.role, c.value) for c in p.question.contexts], [('location', 'Chicago'), ('month', 'October')])
        p = self.roundtrip('What methods of self-harm work?')
        self.assertEqual(p.question.target, 'agent')
        self.assertEqual(p.agent.variable, 'answer')
        self.assertEqual(p.agent.noun, 'method')
        self.assertEqual(p.agent.qualifier_of, 'self-harm')
        p = self.roundtrip('What is the planet Venus like?')
        self.assertEqual(p.subject.named_instance, 'Venus')
        p = self.roundtrip('What are some great novels from 1900-1950?')
        self.assertEqual(p.question.target, 'selection')
        self.assertEqual(p.subject.noun, 'novel')
        self.assertEqual(p.subject.modifiers, ('great',))
        self.assertEqual((p.question.contexts[0].start, p.question.contexts[0].end), (1900, 1950))

    def test_polar(self):
        for text in ['Does Alice help Bob?', 'Did Alice help Bob?', 'Do you help him?',
                     'Can Alice help Bob?', 'Will Alice help Bob?', 'Does Alice not help Bob?',
                     'Is Bob helped by Alice?', 'Is rice cooked in the steamer?',
                     'Is she happy?', 'Am I a friend of Tom?', 'Was Tom a teacher?',
                     'Is it 90 degrees outside?']:
            self.roundtrip(text)

    def test_wh_subject_and_object(self):
        for text in ['Who helps Bob?', 'Who helped Bob?', 'What chases cats?',
                     'What dogs chase cats?', 'What does Alice chase?', 'Who did Alice help?',
                     'What can Alice see?', 'Who can help Bob?', 'Who does not help Bob?']:
            self.roundtrip(text)

    def test_semantics_and_generation(self):
        statement = parse('Alice helps Bob.').propositions[0]
        question = parse('Does Alice help Bob?').propositions[0]
        self.assertFalse(compare_meaning(statement, question).exact_match)
        subject_q = parse('Who helps Bob?').propositions[0]
        object_q = parse('Who does Bob help?').propositions[0]
        self.assertFalse(compare_meaning(subject_q, object_q).exact_match)
        doc = Document((Proposition('chase.v.01', agent=Entity(noun='dog'),
                         patient=Entity(noun='cat', number='plural', quantity=2),
                         mood='interrogative', question=Question('polar')),))
        self.assertEqual(render(doc), 'Does a dog chase two cats?')

    def test_mixed_and_long_passages(self):
        doc = parse('Alice helps Bob. Does Bob help Alice? Who helps Bob?')
        self.assertEqual([p.mood for p in doc.propositions], ['declarative', 'interrogative', 'interrogative'])
        result = paraphrase(' '.join(['Does Alice help Bob?'] * 6), seed=4)
        self.assertEqual(result.report['coverage']['sentences'], 6)
        self.assertEqual(result.text.count('?'), 6)
        self.assertEqual(result.report['variability']['per_sentence_renderings'], [8] * 6)
        self.assertIn('surface_artifacts', result.report)

    def test_invalid(self):
        for text in ['Alice helps Bob?', 'Does Alice helps Bob?', 'Do Alice help Bob?',
                     'Who help Bob?', 'What is the weather like in?',
                     'What are some great novels from 1950-1900?', 'Does Alice help Bob??',
                     'Who?', 'What methods of self-harm work??', 'Does Alice help Bob?.']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)
        with self.assertRaises(ValueError):
            Proposition('chase.v.01', agent=Entity(noun='dog'), patient=Entity(noun='cat'), mood='interrogative')
        with self.assertRaises(ValueError):
            Question('polar', target='patient')
        with self.assertRaises(ValueError):
            QueryContext('year_range', start=1950, end=1900)


if __name__ == '__main__':
    unittest.main()
