"""Additional surface axes over explicitly registered semantic equivalences."""
from itertools import product
import re
from ..lexical import NAMED_ENTITIES, MODIFIER_VARIANTS, named_phrase


def extra_variants(proposition, text):
    slots = []
    aliases = [named_phrase(name, descriptive=style) for name in NAMED_ENTITIES for style in [False, True]]
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(s) for s in sorted(aliases, key=len, reverse=True)) + r')(?!\w)'
    # Match the initial article's sentence capitalization, retaining names' case.
    pattern = pattern.replace('the\\ ', '[Tt]he\\ ')
    for index, match in enumerate(re.finditer(pattern, text)):
        name = next(name for name in NAMED_ENTITIES if match.group().endswith(name))
        options = []
        for descriptive in [False, True]:
            phrase = named_phrase(name, descriptive=descriptive)
            if match.start() == 0:
                phrase = phrase[0].upper() + phrase[1:]
            options.append((phrase, 'descriptive' if descriptive else 'bare'))
        slots.append((match.start(), match.end(), f'named_np_{index + 1}', options))
    # Only vary lexical modifiers actually encoded on noun phrases.
    modifiers = set()
    for role in ('agent', 'patient', 'subject', 'recipient', 'complement', 'related_to', 'experiencer'):
        entity = getattr(proposition, role)
        if entity:
            modifiers.update(entity.modifiers)
    for canonical in sorted(modifiers):
        options = MODIFIER_VARIANTS[canonical]
        if len(options) > 1:
            for index, match in enumerate(re.finditer(r'\b' + re.escape(canonical) + r'\b', text)):
                slots.append((match.start(), match.end(), f'modifier_{canonical}_{index + 1}', [(v, v) for v in options]))
    slots.sort(key=lambda slot: slot[0])
    if any(a[1] > b[0] for a, b in zip(slots, slots[1:])):
        raise ValueError('Overlapping realization slots')
    count = 1
    for slot in slots:
        count *= len(slot[3])
    if count > 4096:
        raise ValueError('Sentence realization space exceeds 4096 variants')
    for selected in product(*(slot[3] for slot in slots)):
        parts, choices, end = [], [], 0
        for slot, (replacement, label) in zip(slots, selected):
            start, stop, name, _ = slot
            parts.extend([text[end:start], replacement])
            choices.append((name, label))
            end = stop
        parts.append(text[end:])
        surface = ''.join(parts)
        requests = [('interrogative', surface)]
        if proposition.question and proposition.question.target == 'selection':
            body = surface.removeprefix('What are ').removesuffix('?')
            requests += [('tell_me', 'Tell me ' + body + '.'), ('give_me', 'Give me ' + body + '.')]
        for request_form, candidate in requests:
            yield candidate, tuple(choices) + (('information_request_form', request_form),)
