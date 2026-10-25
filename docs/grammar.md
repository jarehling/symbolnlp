# symbolnlp

A dependency-free, non-LLM Python prototype for converting short controlled-English
passages into propositions and realizing those propositions as text.
Python 3.10+ is required. No model downloads, API calls, or training are involved.

## Quick start

From this directory:

```sh
python3 -m symbolnlp parse 'Alice assisted Bob. Bob did not help the teacher.'
python3 -m symbolnlp parse 'Alice helps Bob.' | python3 -m symbolnlp render --vocabulary random --structure random --seed 7
python3 -m unittest discover -s tests -v
```

Optionally install with `python3 -m pip install -e .` to use the `symbolnlp` command.
`parse` accepts text as an argument or on stdin. `render` accepts proposition JSON
on stdin. Invalid or unsupported inputs exit with status 2.

```python
from symbolnlp import Document, parse, render

doc = parse('Alice assists Bob.')
assert doc == parse('Bob is helped by Alice.')
print(doc.to_dict())
print(render(doc, vocabulary='random', structure='random', seed=7))
assert parse(render(doc, structure='passive')) == doc
assert Document.from_dict(doc.to_dict()) == doc
```

The proposition representation is independent of sentence voice and, by default,
word choice:

```json
{
  "propositions": [
    {
      "sense": "help.v.01",
      "agent": {"text": "Alice", "number": "singular", "noun": null, "determiner": null, "quantity": null},
      "patient": {"text": "Bob", "number": "singular", "noun": null, "determiner": null, "quantity": null},
      "tense": "present",
      "negated": false,
      "modal": null,
      "lexical_form": null
    }
  ]
}
```

`Document.from_dict` also accepts this format for authoring propositions directly.
The agent and patient are semantic roles, so passive voice does not reverse them.
Separate sentences form an ordered list of asserted propositions.

## Constructing noun phrases from concepts

Surface `text` is optional. For example, this input can be passed directly to
`python3 -m symbolnlp render`:

```json
{
  "propositions": [{
    "sense": "chase.v.01",
    "agent": {"noun": "dog", "number": "singular"},
    "patient": {"noun": "cat", "number": "plural", "quantity": 2},
    "tense": "present"
  }]
}
```

The project produces `A dog chases two cats.`; with `--structure passive`, it
produces `Two cats are chased by a dog.` No prewritten noun phrases are needed.

The Python API also exposes `render_entity(Entity(noun="dog"))`, returning
`a dog`. A noun concept is a lowercase singular lemma. Noun-phrase rules are:

- Explicit `text`, when supplied, is retained for compatibility and exact wording.
  Omit it to construct the phrase from features.
- An explicit `quantity` becomes zero through ten in words, or larger numbers in
  digits, followed by the appropriately numbered noun.
- An explicit `determiner` is retained (`the`, `a`, `an`, `this`, `that`, `these`,
  `those`). Its grammatical number must agree with the entity.
- Otherwise singular count nouns use `a/an`, and plurals have no determiner.
  Choosing an indefinite article is a rendering default, not an inference of
  definiteness from the proposition.

Quantity and determiner combinations are currently rejected rather than silently
losing one feature. Plural generation currently adds `s`; supply explicit text
for irregular or other plural forms. Automatic `a/an` uses the initial vowel
letter, so pronunciation exceptions such as “hour” and “university” require an
explicit determiner. Mass nouns use `mass: true` to suppress the default article and pluralization.
Proper names can still use `text`.

## Vocabulary and variation

- `parse(text)` maps verb variants to a local sense ID.
- `parse(text, normalize=False)` additionally records the original verb lemma.
  The CLI equivalent is `parse --preserve-vocabulary`.
- `render(..., vocabulary='canonical')` uses the first lemma for each sense.
- `vocabulary='preserve'` uses the recorded lemma, falling back to canonical.
- `vocabulary='random'` samples uniformly from the sense's lexical entries.
- `structure='active'`, `'passive'`, or `'random'` selects voice independently
  for each proposition.
- Omit `seed` for nondeterministic choices; supply one for reproducibility.

The curated vocabulary is in `symbolnlp/core.py`, in `LEXICON`. Each verb provides
base, third-person singular, past, and participle forms. Initial senses cover
help/assist/aid/support, chase, cook, give, see, like, admire, follow, and visit. **Aid** is the verb;
**aide** is normally a noun and is intentionally not a verb entry.

Sense IDs are local identifiers, not WordNet IDs. Mapping “support” to helping is
an explicit assumption of this controlled vocabulary. This prototype cannot
distinguish supporting a person from supporting a roof or endorsing a claim.
Applications needing those distinctions should split senses and add contextual
selection rules before admitting the ambiguous forms. Nouns retain their text;
entity identity and noun synonyms are not normalized. Simple regular plural nouns
are reduced to a singular `noun` concept (dogs → dog).

## Supported grammar

One to three sentences with a known event or copular predicate. Declaratives and
base-verb imperatives are supported. Proper names are single capitalized words; common noun
phrases can be bare regular plurals, a determiner (`the`, `a`, `an`, `this`, `that`,
`these`, `those`) plus a single noun, or a numeral plus a single noun.
Numerals support the words zero through ten and nonnegative integer digits.
Determiners and numerals must agree with noun number.

Entities store `noun` (the simple singular noun concept), `determiner`, and
`quantity` separately from their surface `text`. Bare plurals have no determiner
or explicit quantity. These fields retain grammatical distinctions without
inferring universal quantification or generic versus episodic meaning. Rendering
preserves optional noun-phrase text while varying verb vocabulary and voice;
when text is omitted, it constructs the phrase from structured features. Existing
JSON containing only entity text and number remains accepted.

Number and noun normalization use a regular final-`s` heuristic, excluding endings
`ss`, `us`, and `is`. Irregular plurals, other plural suffixes, and ambiguous proper
names ending in `s` need a future noun lexicon; JSON can supply explicit features.

Examples:

```text
Dogs chase cats.
Two dogs chased that cat.
Alice helps Bob.
The teachers did not assist the student.
Bob was helped by Alice.
Alice will visit the teacher.
The student can be assisted by the teachers.
I am a friend of Tom.
Give me the butter.
Rice was cooked in the steamer.
```

Present, simple past, and `will` future are supported, as are `not` negation and
literal modal values `can`, `could`, `may`, `might`, `must`, `should`, and `would`.
Modal propositions store tense as `present`; this is a representation convention,
not an inference about the time expressed by a modal. Negation is clause-level;
modal scope and entailments are not analyzed.

The parser rejects unsupported syntax without returning partial results.
It does not support arbitrary question constructions (see the current README), contractions, coreference resolution, conjunctions,
relative clauses, multiword names, arbitrary adjectives/adverbs, arbitrary prepositional
modifiers, perfect/progressive aspects, quantified logic, or arbitrary argument
frames. Alphabetic words, integer numerals, spaces, periods, and fronting commas are
the accepted input characters; negative integers are supported for temperature.
This is a bounded grammar, not a general English semantic parser, and it performs
no truth checking or inference.

## Copulas, commands, pronouns, and event locations

The decoder and encoder support these additional bounded constructions:

- **Copulas:** `Tom is a teacher.` uses local predicate `be.v.01` with `subject`
  and nominal `complement`. `I am a friend of Tom.` uses `friend.n.01` with
  `subject` and `related_to`; `relation_determiner` retains `a` or `the`.
  The local relational-noun inventory also includes `neighbor` and `member`.
  These predicates do not misuse event agent/patient roles. Agreement, negation,
  past/future, and modals are supported, but plural relational nouns are not.
- **Pronouns:** `pronoun` stores a case-neutral lemma (`i`, `you`, `he`, `she`,
  `it`, `we`, `they`). Rendering selects subject or object forms and applies
  person/number agreement. `I help him.` can become `He is helped by me.`
  Referents remain unresolved; the decoder does not infer that “he” is Tom.
  `you` uses a singular representation by convention with second-person agreement.
- **Imperatives:** `Give me the butter.` has `mood: imperative`, an implied
  `agent` with `pronoun: you`, `recipient` with `pronoun: i`, and butter as
  `patient`. Both double-object and `to` recipient forms are accepted; rendering
  uses `Give the butter to me.` Negative commands use `Do not ...`.
  Commands retain their mood regardless of the requested voice option.
- **Mass nouns:** the parser recognizes rice, butter, water, milk, flour, and
  sand as a small initial lexical class. Structured entities may explicitly use
  `mass: true`. These nouns have singular agreement and accept no count quantity
  or indefinite article in the current grammar.
- **Agentless passives:** `agent: null` retains an unknown/unspecified actor.
  Rendering keeps such events passive even when active voice is requested.
- **Locations:** `adjuncts` stores ordered records such as
  `{"preposition": "in", "entity": {"noun": "steamer", "determiner": "the"}}`.
  Supported prepositions are `in`, `on`, and `at`. They are preserved without
  inferring an instrument or resolving attachment ambiguities. In passives,
  an explicit `by` agent precedes trailing location phrases; an optional `to`
  recipient precedes the `by` agent.

All new structures can be authored without surface text and round-tripped through
JSON. Sense IDs and lexical classes are still local curated placeholders.

## Intransitives, adjective predicates, and ambient temperature

Additional controlled constructions decode and encode without surface text:

| Input | Representation | Canonical rendering |
| --- | --- | --- |
| On the building, a bird sat. | `sit.v.01`, agent bird, no patient, past, location on building | A bird sat on the building. |
| Glory is pleasing to the proud. | `pleasing.a.01`, subject glory, experiencer the proud | Glory is pleasing to the proud. |
| It is 90 degrees outside. | `temperature.n.01`, measurement 90 degrees, location outside | It is 90 degrees outside. |

- **Fronted locations:** one `in/on/at + noun phrase,` can precede an event
  clause. It becomes an event adjunct; rendering puts it after the verb and
  arguments. Arbitrary commas and comma-separated clauses remain unsupported.
- **Intransitives:** `sit` and `sleep` have full base, third-person, past, and
  participle lexical forms, with no patient. They accept tense, negation, modals,
  commands, and locations. Voice options retain active voice for these verbs.
  Objects and passive constructions on these intransitive senses are rejected.
- **Abstract nouns:** glory, pride, happiness, and knowledge join the small
  mass-noun class, allowing bare abstract subjects and objects with singular
  agreement. These are lexical assumptions, not general semantic inference.
- **Adjectival predicates:** pleasing, happy, and proud use separate adjective
  senses and a `subject`. Pleasing optionally takes an `experiencer` introduced
  by `to`. Copular agreement, tense, negation, and modals are supported. Pleasing
  is treated as an adjective here; progressive uses of the verb please are not.
- **Nominalized adjectives:** `the proud/rich/poor/young/old` use entity field
  `nominalized_adjective`, determiner `the`, and plural agreement. They denote
  groups of people in this grammar rather than a noun called “proud”.
- **Temperatures:** `measurement` stores an integer `value`, `unit: degree`,
  and optional `scale: Celsius/Fahrenheit`. Omitted scale stays null; no
  Fahrenheit/Celsius assumption is made. `It` is expletive in this construction,
  so no referential `subject` is stored. Decimal values and other units are not
  supported yet. The plural unit is `degrees`, except for value 1.
- **Location adverbs:** `location_adverb` supports outside, inside, outdoors,
  and indoors on events and the new adjective/temperature predicates.

The temperature example can also be encoded directly:

```python
from symbolnlp import Document, Measurement, Proposition, render

doc = Document((Proposition("temperature.n.01", measurement=Measurement(90),
                            location_adverb="outside"),))
assert render(doc) == "It is 90 degrees outside."
```

All these senses remain local placeholders until lexical-resource integration.

## Lexical resource direction

The target shared sense inventory for common vocabulary is **Open English WordNet**
(https://en-word.net/; source: https://github.com/globalwordnet/english-wordnet).
Integration is pending: current IDs such as `chase.v.01` remain local placeholders,
not verified resource identifiers. A migration must pin a resource release, store
its actual synset/sense IDs, and apply the same inventory to nouns and verbs
(and other supported parts of speech), retaining lemmas as readable labels.

Lexical coverage does not imply grammar coverage. Contextual sense selection,
inflection, argument frames, and grammatical constraints on synonym substitution
remain separate responsibilities of the parser and renderer. Ambiguous words
must not silently select the first listed sense.

## Extending the foundation

The pipeline separates surface parsing, semantic records, and surface realization.
Add lexical entries for verbs with the same transitive frame in `LEXICON`; add
matching parser and realization rules plus round-trip cases for new grammar.
Richer language needs explicit argument frames, entity/coreference handling,
word-sense selection, and a semantic representation for coordination, quantifiers,
and scope. A traditional dependency parser could later supply syntax while these
records and realization rules remain the semantic interface.

Tests exercise synonym normalization, role preservation, JSON round trips,
unsupported input, and rendering/parsing across all lexical forms, tenses,
polarities, numbers, and voice options.

Question syntax and query semantics are documented in the current [README](../README.md#questions).
