"""Inspectable grammar rules, not unrestricted regex paraphrasing."""
from dataclasses import dataclass, field
import re
from typing import Callable

# Slots intentionally admit bounded noun phrases/clauses. A rule matches the
# entire input; there is no substitution in an otherwise unparsed passage.
SLOTS = {
    'owner': r'company|team|school', 'head': r'CEO|director|leader',
    'name': r'Ann|Tom|Alice|Bob', 'other': r'Ann|Tom|Alice|Bob',
    'color': r'red|blue|green', 'noun': r'car|door|box',
    'subject': r'I|you|he|she|we|they|Ann|Tom|Alice|Bob|the team',
    'object': r'the report|the file|the light|the test|the door|the box|rice',
    'item': r'cost|speed|quality', 'item2': r'cost|speed|quality', 'item3': r'cost|speed|quality',
    'plural': r'tests|students|cars', 'number': r'[0-9]+',
    'month': r'October|November|December', 'day': r'[0-9]{1,2}',
    'x': r'the test failed|the file arrived|the team finished',
    'y': r'we left|we waited|the team left',
    'year': r'[0-9]{4}',
    'transitive': r'help|assist|aid|support|chase|visit',
    'thing': r'file|report|test|plan', 'actor': r'we|they',
    'verb': r'failed|worked', 'count_word': r'three|four|five',
    'amount': r'10|20|50', 'amount_word': r'ten|twenty|fifty',

}


@dataclass(frozen=True)
class Form:
    template: str

    def pattern(self):
        parts, seen, end = [], set(), 0
        for match in re.finditer(r'\{(\w+)\}', self.template):
            parts.append(re.escape(self.template[end:match.start()]))
            name = match[1]
            parts.append(f'(?P={name})' if name in seen else f'(?P<{name}>{SLOTS[name]})')
            seen.add(name)
            end = match.end()
        parts.append(re.escape(self.template[end:]))
        return re.compile(''.join(parts), re.IGNORECASE)


@dataclass(frozen=True)
class Rule:
    id: int
    name: str
    level: str
    risk: str
    forms: tuple[Form, ...]
    additional_forms: tuple[tuple[Form, ...], ...] = ()
    requires: tuple[str, ...] = ()
    additional_requirements: tuple[tuple[str, ...], ...] = ()
    rationale: str = 'Curated equivalence in this bounded construction.'
    validate: Callable[[dict], bool] = field(default=lambda slots: True, repr=False, compare=False)

    def decode(self, text):
        for family, forms in enumerate((self.forms,) + self.additional_forms):
            for form in forms:
                match = form.pattern().fullmatch(text)
                if match:
                    slots = {key: value.lower() for key, value in match.groupdict().items()}
                    if self.validate(slots):
                        return {**slots, '_family': family}
        return None

    def outputs(self, slots):
        values = dict(slots)
        for name in ('name', 'other'):
            if name in values:
                values[name] = values[name].capitalize()
        for numeric in ('day', 'number'):
            if numeric in values:
                values[numeric] = str(int(values[numeric]))
        if values.get('head') == 'ceo':
            values['head'] = 'CEO'
        if values.get('subject') in {'i', 'ann', 'tom', 'alice', 'bob'}:
            values['subject'] = values['subject'].capitalize()
        for form in ((self.forms,) + self.additional_forms)[slots.get('_family', 0)]:
            text = form.template.format_map(values)
            if text.startswith('- '):
                text = '\n'.join('- ' + line[2:].capitalize() for line in text.split('\n'))
            yield text[0].upper() + text[1:]

    def requirements_for(self, slots):
        family = slots.get('_family', 0)
        if family and len(self.additional_requirements) >= family:
            return self.additional_requirements[family - 1]
        return self.requires

    def evidence(self):
        return {'id': self.id, 'name': self.name, 'level': self.level,
                'risk': self.risk, 'implementation': 'bounded_rule_grammar',
                'requires': list(self.requires), 'rationale': self.rationale,
                'grammar_families': 1 + len(self.additional_forms),
                'additional_family_requirements': [list(r) for r in self.additional_requirements],
                'templates': [[f.template for f in forms] for forms in (self.forms,) + self.additional_forms]}
