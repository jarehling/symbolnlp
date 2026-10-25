"""All 45 supplied alternations, with deliberately bounded constructions.

Metadata risk labels reproduce the supplied inventory; they are not guarantees.
Guarded rules are not enabled by the labels alone.
"""
from dataclasses import replace
from .model import Form, Rule


def rule(i, name, level, risk, *forms, requires=(), validate=lambda slots: True, rationale=None):
    kwargs = {'requires': requires, 'validate': validate}
    if rationale:
        kwargs['rationale'] = rationale
    return Rule(i, name, level, risk, tuple(Form(form) for form in forms), **kwargs)


def distinct_pair(s):
    return s['item'] != s['item2']


RULES = (
    rule(1, 'saxon_of_genitive', 'noun_phrase', 'L',
         "The {owner}'s {head} resigned.", 'The {head} of the {owner} resigned.'),
    rule(2, 'compound_pp', 'noun_phrase', 'L',
         'Data analysis continued.', 'Analysis of data continued.'),
    rule(3, 'adjective_relative', 'noun_phrase', 'L',
         'The {color} {noun} arrived.', 'The {noun} that is {color} arrived.',
         requires=('property_holds_at_reference_time',)),
    rule(4, 'reduced_relative', 'noun_phrase', 'L',
         'The man standing there is waiting.', 'The man who is standing there is waiting.'),
    rule(5, 'restrictive_relative_pronoun', 'noun_phrase', 'L',
         'The rule that applies is clear.', 'The rule which applies is clear.'),
    rule(6, 'acronym_expansion', 'noun_phrase', 'L',
         'The US has a constitution.', 'The United States has a constitution.'),
    rule(7, 'pronoun_rereference', 'noun_phrase', 'M',
         'The test ran. It failed.', 'The test ran. The test failed.',
         rationale='Only this explicit, unique neuter antecedent; no general coreference inference.'),
    rule(8, 'nominalization_clause', 'noun_phrase', 'M',
         'Their decision to expand surprised us.', 'Their deciding to expand surprised us.',
         requires=('event_nominal_reading',)),
    rule(9, 'commutative_coordination', 'noun_phrase', 'M',
         'We considered {item} and {item2}.', 'We considered {item2} and {item}.',
         requires=('unordered_coordination',), validate=distinct_pair),
    rule(10, 'quantifier_paraphrase', 'noun_phrase', 'M',
         'Most {plural} passed.', 'The majority of {plural} passed.',
         requires=('same_quantifier_domain',)),
    rule(11, 'determiner_paraphrase', 'noun_phrase', 'L',
         'Each student received one file.', 'Every student received one file.',
         requires=('distributive_reading',)),
    rule(12, 'active_passive', 'verb_phrase', 'L',
         'The team wrote the report.', 'The report was written by the team.'),
    rule(13, 'dative', 'verb_phrase', 'L',
         '{name} gave the file to {other}.', '{name} gave {other} the file.'),
    rule(14, 'particle_movement', 'verb_phrase', 'L',
         'Turn off the light.', 'Turn the light off.'),
    rule(15, 'phrasal_latinate', 'verb_phrase', 'M',
         'We found out the truth.', 'We discovered the truth.'),
    rule(16, 'light_verb', 'verb_phrase', 'L',
         'We made a decision to leave.', 'We decided to leave.'),
    rule(17, 'copula_adjective_verb', 'verb_phrase', 'L',
         'The result is dependent on the test.', 'The result depends on the test.'),
    rule(18, 'modal_periphrasis', 'verb_phrase', 'M',
         'She can swim.', 'She is able to swim.', requires=('ability_modal_reading',)),
    rule(19, 'infinitive_gerund', 'verb_phrase', 'M',
         'She began to run.', 'She began running.',
         rationale='Begin + run only; stop/remember and other non-equivalent complements excluded.'),
    rule(20, 'converse_predicate', 'verb_phrase', 'M',
         '{name} precedes {other}.', '{other} follows {name}.',
         requires=('sequence_reading',)),
    rule(21, 'contractions', 'verb_phrase', 'L',
         'I do not know.', "I don't know."),
    rule(22, 'epistemic_hedge', 'verb_phrase', 'M',
         'It may rain.', 'It might rain.', 'It could rain.',
         requires=('epistemic_modal_reading', 'allow_modal_strength_variation')),
    rule(23, 'it_cleft', 'clause', 'M',
         'It was {name} who called.', '{name} called.',
         requires=('allow_focus_change',)),
    rule(24, 'pseudo_cleft', 'clause', 'M',
         'What we need is time.', 'We need time.', requires=('allow_focus_change',)),
    rule(25, 'existential_there', 'clause', 'L',
         'There are three causes.', 'Three causes exist.'),
    rule(26, 'extraposition', 'clause', 'L',
         'That it failed is odd.', 'It is odd that it failed.'),
    rule(27, 'complementizer', 'clause', 'L',
         'She said that it worked.', 'She said it worked.'),
    rule(28, 'conditional_inversion', 'clause', 'L',
         'If I had known, I would have stayed.', 'Had I known, I would have stayed.'),
    rule(29, 'participial_finite_adverbial', 'clause', 'L',
         'Having finished, she left.', 'After she finished, she left.',
         requires=('same_subject_temporal_reading',)),
    rule(30, 'adverbial_clause_position', 'clause', 'L',
         'If {x}, {y}.', '{y} if {x}.'),
    rule(31, 'adverb_position', 'clause', 'M',
         'She quickly finished the test.', 'She finished the test quickly.',
         rationale='Quickly as manner only; only/even scope-changing modifiers excluded.'),
    rule(32, 'litotes', 'clause', 'H',
         'It is not uncommon.', 'It is fairly common.', requires=('bidirectional_entailment',)),
    rule(33, 'request_form', 'clause', 'L',
         'Could you list the causes?', 'Please list the causes.', 'List the causes.',
         requires=('information_request_reading',)),
    rule(34, 'subordination_coordination', 'discourse', 'M',
         'Although {x}, {y}.', '{x}, but {y}.', requires=('concessive_reading',)),
    rule(35, 'sentence_split_merge', 'discourse', 'L',
         'The test failed. This means we must wait.', 'The test failed, which means we must wait.'),
    rule(36, 'connective_synonym', 'discourse', 'M',
         'We waited because {x}.', 'We waited since {x}.', requires=('causal_since_reading',)),
    rule(37, 'discourse_marker', 'discourse', 'L',
         'Additionally, the test failed.', 'Also, the test failed.', 'The test failed.',
         requires=('allow_discourse_marker_loss',)),
    rule(38, 'independent_sentence_order', 'discourse', 'M',
         'Copper conducts electricity. Gold resists corrosion.',
         'Gold resists corrosion. Copper conducts electricity.',
         requires=('independent_assertions',)),
    rule(39, 'parenthetical_appositive_sentence', 'discourse', 'L',
         'Venus (the second planet) is bright.', 'Venus, the second planet, is bright.',
         'Venus is bright. It is the second planet.',
         requires=('allow_information_structure_change',)),
    rule(40, 'list_prose', 'discourse', 'L',
         '- Cost\n- Speed\n- Quality', 'Cost, speed, and quality.',
         requires=('unordered_list',)),
    rule(41, 'list_item_order', 'discourse', 'M',
         '- Cost\n- Speed\n- Quality', '- Quality\n- Cost\n- Speed',
         '- Speed\n- Quality\n- Cost', '- Cost\n- Quality\n- Speed',
         '- Speed\n- Cost\n- Quality', '- Quality\n- Speed\n- Cost',
         requires=('unordered_list',)),
    rule(42, 'number_format', 'orthographic', 'L',
         'There are 3 causes.', 'There are three causes.'),
    rule(43, 'date_format', 'orthographic', 'L',
         'The meeting is on Oct {day}.', 'The meeting is on {day} October.',
         'The meeting is on 10/{day}.', requires=('month_day_locale',),
         validate=lambda s: 1 <= int(s['day']) <= 31),
    rule(44, 'punctuation', 'orthographic', 'L',
         'Venus — the second planet — is bright.', 'Venus (the second planet) is bright.',
         'Venus, the second planet, is bright.'),
    rule(45, 'spelling_variety', 'orthographic', 'L',
         'We analyze the color. They analyze the color.',
         'We analyse the colour. They analyse the colour.',
         rationale='Document-wide US/UK choice; no per-token mixture.'),
)

assert {r.id for r in RULES} == set(range(1, 46))

# Additional independent grammar families. They share method metadata but never
# mix unrelated semantic frames during generation.
EXTRA_FAMILIES = {
    1: [("The {owner}'s {head}", "The {head} of the {owner}")],
    2: [('Data analysis', 'Analysis of data')],
    3: [('The {color} {noun}', 'The {noun} that is {color}')],
    4: [('The man standing there', 'The man who is standing there')],
    5: [('The rule that applies', 'The rule which applies')],
    6: [('The US', 'The United States')],
    8: [('The decision to expand', 'Deciding to expand')],
    10: [('Many {plural} passed.', 'Numerous {plural} passed.')],
    11: [('A lot of {plural} passed.', 'Lots of {plural} passed.')],
    12: [('{name} wrote the {thing}.', 'The {thing} was written by {name}.')],
    13: [('{name} gave the {thing} to {other}.', '{name} gave {other} the {thing}.')],
    14: [('Turn off the {noun}.', 'Turn the {noun} off.')],
    15: [('We put off the meeting.', 'We postponed the meeting.')],
    16: [('We took a look at the test.', 'We looked at the test.')],
    18: [('She must leave.', 'She has to leave.')],
    20: [('{name} sold the file to {other}.', '{other} bought the file from {name}.')],
    21: [('It is ready.', "It's ready."), ('We do not know.', "We don't know.")],
    25: [('There are {number} causes.', '{number} causes exist.')],
    27: [('She said that the test {verb}.', 'She said the test {verb}.')],
    31: [('{name} quickly finished the test.', '{name} finished the test quickly.')],
    33: [('Could you list some great novels?', 'Please list some great novels.', 'List some great novels.')],
    36: [('The test failed. However, we waited.', 'The test failed, but we waited.', 'The test failed. That said, we waited.')],
    42: [('The value is 10%.', 'The value is ten percent.'), ('There are 4 causes.', 'There are four causes.'),
         ('There are 5 causes.', 'There are five causes.')],
    44: [('The test failed; we waited.', 'The test failed. We waited.'),
         ('Cost, speed, and quality.', 'Cost, speed and quality.')],
    45: [('We analyze the color.', 'We analyse the colour.')],
}
RULES = tuple(replace(r, additional_forms=tuple(tuple(Form(f) for f in family)
                     for family in EXTRA_FAMILIES.get(r.id, ()))) for r in RULES)

REQUIREMENT_OVERRIDES = {
    18: (('deontic_modal_reading',),),
    20: (('completed_transfer_reading',),),
    36: (('contrastive_reading',),),
}
RULES = tuple(replace(r, additional_requirements=REQUIREMENT_OVERRIDES.get(r.id, ())) for r in RULES)

# Generalize bounded list members while preserving all three captured items.
LIST_FORMS = (
    '- {item}\n- {item2}\n- {item3}',
    '- {item}\n- {item3}\n- {item2}',
    '- {item2}\n- {item}\n- {item3}',
    '- {item2}\n- {item3}\n- {item}',
    '- {item3}\n- {item}\n- {item2}',
    '- {item3}\n- {item2}\n- {item}',
)
LIST_EXTRA = {
    40: ((LIST_FORMS[0], '{item}, {item2}, and {item3}.'),),
    41: (LIST_FORMS,),
    44: (('{item}, {item2}, and {item3}.', '{item}, {item2} and {item3}.'),),
    21: (("{actor} do not {transitive} {name}.", "{actor} don't {transitive} {name}."),),
}
RULES = tuple(replace(r, additional_forms=r.additional_forms + tuple(
    tuple(Form(f) for f in family) for family in LIST_EXTRA.get(r.id, ())),
    validate=(lambda s: not {'item', 'item2', 'item3'} <= s.keys() or
              len({s['item'], s['item2'], s['item3']}) == 3)
    if r.id in {40, 41, 44} else r.validate) for r in RULES)
