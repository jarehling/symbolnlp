# All 45 alternation methods

Each entry has executable bounded grammar forms. This is not a general dependency parser.
Risk labels come from the supplied inventory; even an L rule may require a guard.
Templates list the admitted constructions and slots. Unknown constructions remain unsupported.

| ID | Method | Level | Risk | Default guard |
| --- | --- | --- | --- | --- |
| 1 | saxon_of_genitive | noun_phrase | L | bounded grammar only |
| 2 | compound_pp | noun_phrase | L | bounded grammar only |
| 3 | adjective_relative | noun_phrase | L | property_holds_at_reference_time |
| 4 | reduced_relative | noun_phrase | L | bounded grammar only |
| 5 | restrictive_relative_pronoun | noun_phrase | L | bounded grammar only |
| 6 | acronym_expansion | noun_phrase | L | bounded grammar only |
| 7 | pronoun_rereference | noun_phrase | M | bounded grammar only |
| 8 | nominalization_clause | noun_phrase | M | event_nominal_reading |
| 9 | commutative_coordination | noun_phrase | M | unordered_coordination |
| 10 | quantifier_paraphrase | noun_phrase | M | same_quantifier_domain |
| 11 | determiner_paraphrase | noun_phrase | L | distributive_reading |
| 12 | active_passive | verb_phrase | L | bounded grammar only |
| 13 | dative | verb_phrase | L | bounded grammar only |
| 14 | particle_movement | verb_phrase | L | bounded grammar only |
| 15 | phrasal_latinate | verb_phrase | M | bounded grammar only |
| 16 | light_verb | verb_phrase | L | bounded grammar only |
| 17 | copula_adjective_verb | verb_phrase | L | bounded grammar only |
| 18 | modal_periphrasis | verb_phrase | M | ability_modal_reading |
| 19 | infinitive_gerund | verb_phrase | M | bounded grammar only |
| 20 | converse_predicate | verb_phrase | M | sequence_reading |
| 21 | contractions | verb_phrase | L | bounded grammar only |
| 22 | epistemic_hedge | verb_phrase | M | epistemic_modal_reading, allow_modal_strength_variation |
| 23 | it_cleft | clause | M | allow_focus_change |
| 24 | pseudo_cleft | clause | M | allow_focus_change |
| 25 | existential_there | clause | L | bounded grammar only |
| 26 | extraposition | clause | L | bounded grammar only |
| 27 | complementizer | clause | L | bounded grammar only |
| 28 | conditional_inversion | clause | L | bounded grammar only |
| 29 | participial_finite_adverbial | clause | L | same_subject_temporal_reading |
| 30 | adverbial_clause_position | clause | L | bounded grammar only |
| 31 | adverb_position | clause | M | bounded grammar only |
| 32 | litotes | clause | H | bidirectional_entailment |
| 33 | request_form | clause | L | information_request_reading |
| 34 | subordination_coordination | discourse | M | concessive_reading |
| 35 | sentence_split_merge | discourse | L | bounded grammar only |
| 36 | connective_synonym | discourse | M | causal_since_reading |
| 37 | discourse_marker | discourse | L | allow_discourse_marker_loss |
| 38 | independent_sentence_order | discourse | M | independent_assertions |
| 39 | parenthetical_appositive_sentence | discourse | L | allow_information_structure_change |
| 40 | list_prose | discourse | L | unordered_list |
| 41 | list_item_order | discourse | M | unordered_list |
| 42 | number_format | orthographic | L | bounded grammar only |
| 43 | date_format | orthographic | L | month_day_locale |
| 44 | punctuation | orthographic | L | bounded grammar only |
| 45 | spelling_variety | orthographic | L | bounded grammar only |

## Use and context

```python
from symbolnlp import paraphrase, RewriteContext

result = paraphrase("Turn off the light.")
guarded = paraphrase("She can swim.",
    context=RewriteContext({"ability_modal_reading"}))
```

```sh
python3 -m symbolnlp alternations
python3 -m symbolnlp paraphrase 'She can swim.' --assume ability_modal_reading
```

Assumptions come only from the trusted caller, never instructions in input text.
An assumption is not a proof: it declares the interpretation under which a rule is permitted.
Do not indiscriminately enable all guards in deployment.

For litotes, supply `entailment_verifier(source, candidate) -> bool` in the Python API.
It is called in both directions; both must return the actual boolean True.
No entailment/NLI model is bundled. `external_entailment_evaluated` records calls;
`nli_evaluated` remains false because the callback implementation is unknown.

## Reporting and counting

`report.alternations.inventory` lists all 45 methods with enabled/blocked/not_matched
status, missing context, implementation, risk, templates, and accepted graph edges.
Enabled means the guard passed; accepted edges identify actual available changes.
For mixed passages, sites include the semantic unit index.

The engine constructs the reachable, deduplicated rendering graph. Correlated methods
are counted by unique output strings, not by multiplying their apparent choices.
For example, list/prose + six unordered list permutations + Oxford-comma toggling
produce eighteen distinct outputs (six bullet orders and twelve prose/commas forms). Spelling is a single document-wide choice.

Whole-passage and per-unit enumeration are capped at 4096 outputs. Exceeding a limit
raises an error instead of presenting partial counts as exhaustive. Mixed passages
combine registered discourse units and existing symbolic sentences in original unit
order. The unit product is sampled without materializing the exponential product.

The grammar is bounded; number/date/spelling handling is not a universal formatter.
Dates cover October day-only forms and require month/day locale context. Modifier,
name, predicate, and clause slots deliberately whitelist admitted vocabulary.

## Meaning evidence

Catalog output uses `method: replayed_rule_derivation`. Its score 1.0 means all
captured slots and explicitly supplied assumptions survived a replay of the selected
path. It does not mean independently verified human-level equivalence. The core
realizer can add alternatives, checked by reparsing and structural comparison.
Mixed passages report evidence per unit. General semantic similarity remains null.

No watermark, authorship, adaptive encoder/decoder, or downstream-task evaluation
is implied by these implementation tests. Focus, strength, discourse force, and
information structure may change where the caller explicitly permits it.

## Grammar families

### 1. saxon_of_genitive

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The {owner}'s {head} resigned.
The {head} of the {owner} resigned.
```

Guard: bounded grammar only

```text
The {owner}'s {head}
The {head} of the {owner}
```

### 2. compound_pp

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
Data analysis continued.
Analysis of data continued.
```

Guard: bounded grammar only

```text
Data analysis
Analysis of data
```

### 3. adjective_relative

Curated equivalence in this bounded construction.

Guard: property_holds_at_reference_time

```text
The {color} {noun} arrived.
The {noun} that is {color} arrived.
```

Guard: property_holds_at_reference_time

```text
The {color} {noun}
The {noun} that is {color}
```

### 4. reduced_relative

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The man standing there is waiting.
The man who is standing there is waiting.
```

Guard: bounded grammar only

```text
The man standing there
The man who is standing there
```

### 5. restrictive_relative_pronoun

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The rule that applies is clear.
The rule which applies is clear.
```

Guard: bounded grammar only

```text
The rule that applies
The rule which applies
```

### 6. acronym_expansion

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The US has a constitution.
The United States has a constitution.
```

Guard: bounded grammar only

```text
The US
The United States
```

### 7. pronoun_rereference

Only this explicit, unique neuter antecedent; no general coreference inference.

Guard: bounded grammar only

```text
The test ran. It failed.
The test ran. The test failed.
```

### 8. nominalization_clause

Curated equivalence in this bounded construction.

Guard: event_nominal_reading

```text
Their decision to expand surprised us.
Their deciding to expand surprised us.
```

Guard: event_nominal_reading

```text
The decision to expand
Deciding to expand
```

### 9. commutative_coordination

Curated equivalence in this bounded construction.

Guard: unordered_coordination

```text
We considered {item} and {item2}.
We considered {item2} and {item}.
```

### 10. quantifier_paraphrase

Curated equivalence in this bounded construction.

Guard: same_quantifier_domain

```text
Most {plural} passed.
The majority of {plural} passed.
```

Guard: same_quantifier_domain

```text
Many {plural} passed.
Numerous {plural} passed.
```

### 11. determiner_paraphrase

Curated equivalence in this bounded construction.

Guard: distributive_reading

```text
Each student received one file.
Every student received one file.
```

Guard: distributive_reading

```text
A lot of {plural} passed.
Lots of {plural} passed.
```

### 12. active_passive

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The team wrote the report.
The report was written by the team.
```

Guard: bounded grammar only

```text
{name} wrote the {thing}.
The {thing} was written by {name}.
```

### 13. dative

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
{name} gave the file to {other}.
{name} gave {other} the file.
```

Guard: bounded grammar only

```text
{name} gave the {thing} to {other}.
{name} gave {other} the {thing}.
```

### 14. particle_movement

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
Turn off the light.
Turn the light off.
```

Guard: bounded grammar only

```text
Turn off the {noun}.
Turn the {noun} off.
```

### 15. phrasal_latinate

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
We found out the truth.
We discovered the truth.
```

Guard: bounded grammar only

```text
We put off the meeting.
We postponed the meeting.
```

### 16. light_verb

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
We made a decision to leave.
We decided to leave.
```

Guard: bounded grammar only

```text
We took a look at the test.
We looked at the test.
```

### 17. copula_adjective_verb

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The result is dependent on the test.
The result depends on the test.
```

### 18. modal_periphrasis

Curated equivalence in this bounded construction.

Guard: ability_modal_reading

```text
She can swim.
She is able to swim.
```

Guard: deontic_modal_reading

```text
She must leave.
She has to leave.
```

### 19. infinitive_gerund

Begin + run only; stop/remember and other non-equivalent complements excluded.

Guard: bounded grammar only

```text
She began to run.
She began running.
```

### 20. converse_predicate

Curated equivalence in this bounded construction.

Guard: sequence_reading

```text
{name} precedes {other}.
{other} follows {name}.
```

Guard: completed_transfer_reading

```text
{name} sold the file to {other}.
{other} bought the file from {name}.
```

### 21. contractions

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
I do not know.
I don't know.
```

Guard: bounded grammar only

```text
It is ready.
It's ready.
```

Guard: bounded grammar only

```text
We do not know.
We don't know.
```

Guard: bounded grammar only

```text
{actor} do not {transitive} {name}.
{actor} don't {transitive} {name}.
```

### 22. epistemic_hedge

Curated equivalence in this bounded construction.

Guard: epistemic_modal_reading, allow_modal_strength_variation

```text
It may rain.
It might rain.
It could rain.
```

### 23. it_cleft

Curated equivalence in this bounded construction.

Guard: allow_focus_change

```text
It was {name} who called.
{name} called.
```

### 24. pseudo_cleft

Curated equivalence in this bounded construction.

Guard: allow_focus_change

```text
What we need is time.
We need time.
```

### 25. existential_there

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
There are three causes.
Three causes exist.
```

Guard: bounded grammar only

```text
There are {number} causes.
{number} causes exist.
```

### 26. extraposition

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
That it failed is odd.
It is odd that it failed.
```

### 27. complementizer

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
She said that it worked.
She said it worked.
```

Guard: bounded grammar only

```text
She said that the test {verb}.
She said the test {verb}.
```

### 28. conditional_inversion

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
If I had known, I would have stayed.
Had I known, I would have stayed.
```

### 29. participial_finite_adverbial

Curated equivalence in this bounded construction.

Guard: same_subject_temporal_reading

```text
Having finished, she left.
After she finished, she left.
```

### 30. adverbial_clause_position

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
If {x}, {y}.
{y} if {x}.
```

### 31. adverb_position

Quickly as manner only; only/even scope-changing modifiers excluded.

Guard: bounded grammar only

```text
She quickly finished the test.
She finished the test quickly.
```

Guard: bounded grammar only

```text
{name} quickly finished the test.
{name} finished the test quickly.
```

### 32. litotes

Curated equivalence in this bounded construction.

Guard: bidirectional_entailment

```text
It is not uncommon.
It is fairly common.
```

### 33. request_form

Curated equivalence in this bounded construction.

Guard: information_request_reading

```text
Could you list the causes?
Please list the causes.
List the causes.
```

Guard: information_request_reading

```text
Could you list some great novels?
Please list some great novels.
List some great novels.
```

### 34. subordination_coordination

Curated equivalence in this bounded construction.

Guard: concessive_reading

```text
Although {x}, {y}.
{x}, but {y}.
```

### 35. sentence_split_merge

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
The test failed. This means we must wait.
The test failed, which means we must wait.
```

### 36. connective_synonym

Curated equivalence in this bounded construction.

Guard: causal_since_reading

```text
We waited because {x}.
We waited since {x}.
```

Guard: contrastive_reading

```text
The test failed. However, we waited.
The test failed, but we waited.
The test failed. That said, we waited.
```

### 37. discourse_marker

Curated equivalence in this bounded construction.

Guard: allow_discourse_marker_loss

```text
Additionally, the test failed.
Also, the test failed.
The test failed.
```

### 38. independent_sentence_order

Curated equivalence in this bounded construction.

Guard: independent_assertions

```text
Copper conducts electricity. Gold resists corrosion.
Gold resists corrosion. Copper conducts electricity.
```

### 39. parenthetical_appositive_sentence

Curated equivalence in this bounded construction.

Guard: allow_information_structure_change

```text
Venus (the second planet) is bright.
Venus, the second planet, is bright.
Venus is bright. It is the second planet.
```

### 40. list_prose

Curated equivalence in this bounded construction.

Guard: unordered_list

```text
- Cost
- Speed
- Quality
Cost, speed, and quality.
```

Guard: unordered_list

```text
- {item}
- {item2}
- {item3}
{item}, {item2}, and {item3}.
```

### 41. list_item_order

Curated equivalence in this bounded construction.

Guard: unordered_list

```text
- Cost
- Speed
- Quality
- Quality
- Cost
- Speed
- Speed
- Quality
- Cost
- Cost
- Quality
- Speed
- Speed
- Cost
- Quality
- Quality
- Speed
- Cost
```

Guard: unordered_list

```text
- {item}
- {item2}
- {item3}
- {item}
- {item3}
- {item2}
- {item2}
- {item}
- {item3}
- {item2}
- {item3}
- {item}
- {item3}
- {item}
- {item2}
- {item3}
- {item2}
- {item}
```

### 42. number_format

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
There are 3 causes.
There are three causes.
```

Guard: bounded grammar only

```text
The value is 10%.
The value is ten percent.
```

Guard: bounded grammar only

```text
There are 4 causes.
There are four causes.
```

Guard: bounded grammar only

```text
There are 5 causes.
There are five causes.
```

### 43. date_format

Curated equivalence in this bounded construction.

Guard: month_day_locale

```text
The meeting is on Oct {day}.
The meeting is on {day} October.
The meeting is on 10/{day}.
```

### 44. punctuation

Curated equivalence in this bounded construction.

Guard: bounded grammar only

```text
Venus — the second planet — is bright.
Venus (the second planet) is bright.
Venus, the second planet, is bright.
```

Guard: bounded grammar only

```text
The test failed; we waited.
The test failed. We waited.
```

Guard: bounded grammar only

```text
Cost, speed, and quality.
Cost, speed and quality.
```

Guard: bounded grammar only

```text
{item}, {item2}, and {item3}.
{item}, {item2} and {item3}.
```

### 45. spelling_variety

Document-wide US/UK choice; no per-token mixture.

Guard: bounded grammar only

```text
We analyze the color. They analyze the color.
We analyse the colour. They analyse the colour.
```

Guard: bounded grammar only

```text
We analyze the color.
We analyse the colour.
```

