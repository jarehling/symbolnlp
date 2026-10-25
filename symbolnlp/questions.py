"""Question syntax and query semantics. Never retrieves or generates answers."""
from dataclasses import replace
import re
import random
from .core import (Document, Entity, MONTHS, MODALS, Proposition, QueryContext, Question,
                   UnsupportedText, VERBS, _be, _case_entity, _entity, _parse_sentence,
                   _third_singular, render, render_entity)


def _consume_subject(tokens):
    # Prefer the longest bounded noun phrase that parses; no arbitrary text capture.
    for size in range(min(5, len(tokens)), 0, -1):
        try:
            return _case_entity(tokens[:size], 'subject'), tokens[size:]
        except ValueError:
            pass
    raise UnsupportedText('Missing interrogative subject')


def _lower_initial(text, entity):
    if entity and (entity.noun or entity.pronoun and entity.pronoun != 'i'):
        return text[0].lower() + text[1:]
    return text


def _context(tokens):
    contexts = []
    while tokens:
        if len(tokens) >= 2 and tokens[0].lower() == 'in':
            value = tokens[1]
            contexts.append(QueryContext('month' if value in MONTHS else 'location', value=value))
            tokens = tokens[2:]
        elif len(tokens) == 2 and tokens[0].lower() == 'from':
            match = re.fullmatch(r'(\d{4})-(\d{4})', tokens[1])
            if not match:
                raise UnsupportedText('Expected YYYY-YYYY range')
            contexts.append(QueryContext('year_range', start=int(match[1]), end=int(match[2])))
            tokens = []
        else:
            raise UnsupportedText('Unsupported question context')
    return tuple(contexts)


def parse_question(sentence, normalize=True):
    tokens = sentence.split()
    low = [t.lower() for t in tokens]
    if not tokens:
        raise UnsupportedText('Empty question')
    # Description query: the unknown is a description, not an asserted predicate.
    if low[:2] in [['what', 'is'], ['what', 'are']]:
        like = next((i for i, t in enumerate(low[2:], 2) if t == 'like'), None)
        if like is not None:
            subject = _case_entity(tokens[2:like], 'subject')
            if low[1] != _be(subject, 'present'):
                raise UnsupportedText('Question copula does not agree')
            return Proposition('describe.v.01', subject=subject, mood='interrogative',
                               question=Question('wh', 'description', 'what', _context(tokens[like + 1:])))
        if low[:3] == ['what', 'are', 'some']:
            boundary = next((i for i, t in enumerate(low[3:], 3) if t == 'from'), len(tokens))
            restrictor = replace(_entity(tokens[2:boundary]), variable='answer')
            if restrictor.number != 'plural':
                raise UnsupportedText('What are some requires plural restriction')
            return Proposition('select.n.01', subject=restrictor, mood='interrogative',
                               question=Question('wh', 'selection', 'what', _context(tokens[boundary:])))
    if low[0] in {'what', 'who'}:
        wh = low[0]
        inverted_object = False
        if len(low) > 1 and low[1] in {'do', 'does', 'did'} | MODALS:
            try:
                _consume_subject(tokens[2:])
                inverted_object = True
            except ValueError:
                pass
        if inverted_object:
            # Object-wh: reconstruct a complete proposition with a role placeholder.
            declarative = _inverted(tokens[1:] + ['Queryanswer'], normalize)
            if declarative.patient is None or declarative.patient.text != 'Queryanswer':
                raise UnsupportedText('Only direct-object wh questions supported here')
            return replace(declarative, patient=Entity(variable='answer'), mood='interrogative',
                           question=Question('wh', 'patient', wh))
        verb_at = next((i for i, t in enumerate(low[1:], 1) if any(t in forms for variants in VERBS.values() for forms in variants)), None)
        if verb_at is None:
            raise UnsupportedText('Expected a known predicate in subject-wh question')
        auxiliary_at = next((i for i in range(1, verb_at) if low[i] in MODALS | {'will', 'do', 'does', 'did'}), None)
        if auxiliary_at is not None:
            verb_at = auxiliary_at
        restriction = (Entity(variable='answer') if verb_at == 1 else
                       replace(_entity(['the'] + tokens[1:verb_at]), determiner=None, text=None, variable='answer'))
        # Use an entity with the same agreement to let the existing grammar validate.
        placeholder = 'Queryanswer' if restriction.number == 'singular' else 'the queryanswers'
        statement = _parse_sentence(placeholder + ' ' + ' '.join(tokens[verb_at:]), normalize)
        return replace(statement, agent=restriction, mood='interrogative',
                       question=Question('wh', 'agent', wh))
    statement = _inverted(tokens, normalize)
    return replace(statement, mood='interrogative', question=Question('polar'))


def _inverted(tokens, normalize=True):
    first = tokens[0].lower()
    if first not in {'am', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'will'} | MODALS:
        raise UnsupportedText('Expected wh syntax or subject-auxiliary inversion')
    subject, remainder = _consume_subject(tokens[1:])
    subject_text = render_entity(subject)
    if first in {'do', 'does', 'did'}:
        negative = remainder[:1] == ['not']
        rest = remainder[1:] if negative else remainder
        if not rest:
            raise UnsupportedText('Missing question verb')
        forms = next((f for variants in VERBS.values() for f in variants if f[0] == rest[0].lower()), None)
        if forms is None:
            raise UnsupportedText('Do-support requires known base verb')
        expected = 'did' if first == 'did' else 'does' if _third_singular(subject) else 'do'
        if first != expected:
            raise UnsupportedText('Question auxiliary does not agree')
        if negative:
            predicate = first + ' not ' + ' '.join(rest)
        else:
            predicate = (forms[2] if first == 'did' else forms[1 if _third_singular(subject) else 0]) + ' ' + ' '.join(rest[1:])
        return _parse_sentence(subject_text + ' ' + predicate.strip(), normalize)
    return _parse_sentence(subject_text + ' ' + first + ' ' + ' '.join(remainder), normalize)


def render_question(p, *, vocabulary='canonical', structure='active', seed=None):
    q = p.question
    if q.kind == 'wh':
        structure = 'active'
    elif structure == 'random':
        from .core import INTRANSITIVE
        structure = random.Random(seed).choice(['active', 'passive']) if p.sense in VERBS and p.sense not in INTRANSITIVE and p.agent is not None else 'active'
    contexts = ''.join(' from ' + str(c.start) + '-' + str(c.end) if c.role == 'year_range'
                       else ' in ' + c.value for c in q.contexts)
    if q.target == 'description':
        return f'What {_be(p.subject, p.tense)} {render_entity(p.subject)} like{contexts}?'
    if q.target == 'selection':
        return f'What are {render_entity(p.subject)}{contexts}?'
    if q.kind == 'wh' and q.target == 'agent':
        entity = p.agent
        phrase = q.wh_word.capitalize()
        if entity.noun:
            phrase += ' ' + render_entity(replace(entity, variable=None, determiner=None, text=None)).removeprefix('a ').removeprefix('an ')
        placeholder = Entity(text='Queryanswer', number=entity.number)
        statement = replace(p, agent=placeholder, mood='declarative', question=None)
        surface = render(Document((statement,)), vocabulary=vocabulary, structure='active', seed=seed)
        return phrase + surface[len('Queryanswer'):-1] + '?'
    original = p
    if q.kind == 'wh':
        p = replace(p, patient=Entity(text='Queryanswer'), mood='declarative', question=None)
    statement = replace(p, mood='declarative', question=None)
    surface = render(Document((statement,)), vocabulary=vocabulary, structure=structure if q.kind == 'polar' else 'active', seed=seed)[:-1]
    # Locate the rendered grammatical subject by its entity, not arbitrary words.
    passive = original.agent is None or (structure == 'passive' and original.patient is not None)
    subject = original.patient if passive else original.agent
    if subject is None:
        subject = original.subject
    if subject is None:  # ambient-temperature expletive
        subject = Entity(pronoun='it')
    subject_surface = render_entity(subject)
    prefix = subject_surface[0].upper() + subject_surface[1:] + ' '
    if not surface.startswith(prefix):
        raise ValueError('Cannot identify question subject in realization')
    predicate = surface[len(prefix):]
    head, _, tail = predicate.partition(' ')
    auxiliaries = {'am', 'is', 'are', 'was', 'were', 'will', 'do', 'does', 'did'} | MODALS
    if head not in auxiliaries:
        forms = next(f for variants in VERBS.values() for f in variants if head in f)
        head = 'did' if original.tense == 'past' else 'does' if _third_singular(subject) else 'do'
        tail = forms[0] + (' ' + tail if tail else '')
    result = head.capitalize() + ' ' + _lower_initial(subject_surface, subject) + (' ' + tail if tail else '')
    if q.kind == 'wh':
        if not result.endswith(' Queryanswer'):
            raise ValueError('Object-wh modifiers not supported in rendering')
        result = q.wh_word.capitalize() + ' ' + result[0].lower() + result[1:-len(' Queryanswer')]
    return result + '?'
