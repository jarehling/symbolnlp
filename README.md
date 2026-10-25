# symbolnlp

A non-LLM paraphrasing tool for inter-agent text channels. It regenerates text
from a structured meaning representation, samples among verified rephrasings,
and reports **surface artifacts**, **how much variation is available**, and
**what meaning was checked**.

The purpose is to reduce dependence on a source agent's wording. The current
backend is a dependency-free **controlled-English prototype**, not a general
paraphraser for arbitrary LLM output. It has not demonstrated removal of an
unknown watermark or covert signal. Python 3.10+ is required.

## Use

```sh
# JSON containing output text and both reports
python3 -m symbolnlp paraphrase 'Alice helps Bob.'

# Only the rewritten text, suitable for a receiving agent
python3 -m symbolnlp paraphrase 'Alice helps Bob.' --text-only

# Reproducible debugging; do not use a fixed seed in deployment
python3 -m symbolnlp paraphrase 'Alice helps Bob.' --seed 7

# A passage on stdin; optional editable installation exposes `symbolnlp`
python3 -m symbolnlp paraphrase < passage.txt
python3 -m unittest discover -s tests -v
python3 -m examples.rewording_demo
```

```python
from symbolnlp import paraphrase

result = paraphrase('Alice helps Bob. On the building, a bird sat.')
if result.text is not None:
    send_to_receiver = result.text
    trusted_audit_report = result.report
else:
    unsupported_sentences = result.report['coverage']['failures']
```

Keep reports on a trusted audit path. Input-dependent metadata can itself carry
signals; do not forward the full result JSON to an agent whose input channel is
being constrained. The tool returns data; it sends no messages or network calls.

## Surface-artifact report

Every result includes `report.surface_artifacts`, even if normalization or
semantic decoding rejects the passage. Inspection uses the **original input**
before whitespace or Unicode normalization can erase evidence.

Detected observations include:

- Possible Greek/Cyrillic homoglyphs, mixed-script words, and Unicode compatibility
  characters such as fullwidth letters. Candidates are reported, not substituted.
- Zero-width characters, variation selectors, bidirectional controls, and other
  control/format characters, with Unicode names and code points.
- Tabs, repeated spaces, nonstandard whitespace, leading/trailing line spaces,
  repeated blank lines, and mixed newline styles.
- Typographic quotes/dashes/ellipsis, repeated punctuation, spacing before
  punctuation, and missing spaces after sentence punctuation.
- Markdown headings, mixed bullet markers, numbered lists, code fences, inline
  code/emphasis markers, links/images, blockquotes, and hard line breaks.
- All-caps words, internal capitals, and lowercase sentence initials.

Findings are grouped by category/kind/details, with full occurrence counts and
bounded position samples. Offsets are zero-based Unicode code-point offsets;
lines and columns are one-based. Unicode names/code points and diagnostic labels
are used instead of source excerpts. The default limits are 200 finding groups
and 20 positions per group; omitted information is explicitly counted.

```python
from symbolnlp.rewording import inspect_surface

artifacts = inspect_surface("Аlice\u200b  helps Bob!!!")  # Cyrillic A
for finding in artifacts["findings"]:
    print(finding["kind"], finding["count"], finding["positions"])
```

This inspection is also available independently of paraphrasing. Findings are
observations, **not evidence of covert intent**: legitimate acronyms, typography,
non-English text, and markdown can trigger them. The confusable table is small,
not comprehensive Unicode spoof detection. Markdown inspection is lexical rather
than an AST parser; findings may overlap, including markers inside code blocks.
No findings does not establish that a passage is free of hidden signals.
Inspection does not change the existing canonicalization/rejection policy.

## Variability report

For `Alice helps Bob.`, the current backend has four verb lemmas and two voices:
**2 choice parameters, 8 distinct renderings, log2(8) = 3 bits of output choice**.
For example, `Bob is assisted by Alice.` is one rendering. These are bounds for
this implementation's candidate set, not the number of all possible English
paraphrases or a measurement of remaining covert-channel capacity.

The report includes:

- Applicable parameters and their values at each sentence position: verb lemma,
  active/passive voice, location placement, and recipient construction.
- Counts of deduplicated, structurally verified sentence renderings.
- The product of those counts across a passage, plus its base-2 logarithm.
- The number of variable sentence positions, rejected candidates, and sampled
  passage candidates (default 16; configurable from 1 to 256).

Counts account for dependencies. `Alice gives me the butter.` has three outputs:
active double object, active `to`, and patient-passive `to`; it does not have
four independent voice/recipient combinations. Counts are serialized as decimal
strings to avoid JSON/JavaScript integer precision loss.

Length alone does not guarantee variability: fifty repetitions of `Alice helps
Bob.` have 100 applicable choice parameters and 8^50 possible renderings, while
fifty temperature statements may each offer only one rendering. Low-variation
inputs are reported honestly with `status: unchanged` when appropriate.

## Meaning report

Every sentence rendering is decoded again and compared with the input's encoded
proposition. A final independent comparison checks the selected output against
the normalized input. Any change to encoded roles, predicate, negation, modality,
tense, mood, quantity, determiner, measurement, or location fails the filter.
Sentence order is preserved. Names remain identity-bearing; redundant surface
text and original verb spelling are excluded from semantic comparison.

`meaning.score` is the equal-weight agreement of encoded top-level semantic
fields, averaged over sentences. A successfully accepted output scores **1.0**
because the filter requires every field to agree. This is **structural agreement
within the grammar and curated sense mappings**, not a calibrated probability,
a general semantic similarity score, or an independent human/NLI assessment.
`general_semantic_similarity` is null and `nli_evaluated` is false.

The mapping of help/assist/aid/support to one local sense is an explicit lexical
assumption. Context, scope, discourse, register, and nuances absent from the
representation are not covered by this metric. General language support needs a
stronger semantic backend and independent fidelity evaluation.

## Pipeline and randomness

1. **Canonicalize:** Unicode NFKC and whitespace normalization. Non-whitespace
   control/format characters are rejected rather than silently joining words.
   No arbitrary homoglyph mapping or markdown/code rewriting is performed.
2. **Decode and regenerate:** controlled sentences become propositions. Surface
   noun text is discarded where structured features exist; names are retained.
   Candidate wording is generated from those features, not copied from input.
3. **Filter:** reparse every candidate and require exact encoded meaning agreement.
4. **Sample:** use OS-backed randomness to select a uniform distinct sample of
   passage renderings, then uniformly choose one candidate. Passage combinations
   are sampled as mixed-radix indices, without materializing an exponential list.
5. **Verify and report:** recheck the selected passage and attach diagnostics.

The original wording remains eligible. Forcing a different output would make
selection depend on a source-controlled wording choice. For inputs mapped to the
same normalized representation and candidate set, sampling does not depend on
which spelling/voice the source used. Repeated calls can legitimately return the
same output. There is no rewrite cache; production seeds are not recorded.

## Coverage and failure behavior

The paraphraser supports up to 1000 controlled-English sentences delimited by periods or question marks;
it is no longer limited to the core parser's three-sentence `Document`. Coverage
must be complete. One unsupported sentence yields `status: unsupported`,
`text: null`, coverage diagnostics, and null meaning/variability reports. The CLI
exits with status 2. Unsupported text is never silently passed through.

Code, structured data, general markdown, complex discourse, and arbitrary LLM
prose currently need another backend or a separately designed handling path.
The original `parse` and `render` commands and Python APIs remain available.
See [the grammar reference](docs/grammar.md) for supported constructions and
[the architecture and evaluation plan](docs/architecture.md) for extension work.

## Questions

Questions are represented semantically, not just as statements with a different
terminator. `mood: interrogative` requires a `question` record. The pipeline
preserves questions as questions and never supplies answers.

- `Question("polar")` asks whether a proposition holds. Parsing supports
  auxiliary/copula inversion and do-support: `Does Alice help Bob?`,
  `Can Alice help Bob?`, `Is Bob helped by Alice?`, `Is she happy?`.
- Wh questions bind an `answer` variable in an explicit role. `Who helps Bob?`
  targets the agent; `What does Alice chase?` targets the patient. Restricted
  subject queries such as `What dogs chase cats?` retain noun and number.
  Active/passive variation is currently limited to polar questions; wh queries
  use canonical active syntax to preserve the requested role.
- Description requests such as `What is the weather like in Chicago in October?`
  use local query predicate `describe.v.01`, with a subject and typed location
  and month contexts. `What is the planet Venus like?` retains Venus as the named
  instance of the noun planet, rather than losing it inside raw surface text.
- `What methods of self-harm work?` is a subject-wh query with method as the
  plural restriction, self-harm as its noun qualifier, and local predicate
  `work.v.01`. The system only encodes/rephrases the question; it does not
  enumerate methods or provide any answers.
- `What are some great novels from 1900-1950?` uses `select.n.01`, retaining
  `some`, the modifier `great`, and an inclusive year-range constraint.

The four description/restricted-selection examples currently have one verified
rendering each, so their variability report is honest about unchanged wording.
Polar questions about help can use the existing synonym and voice alternatives.
Question kind, requested role, variable restrictions, and contexts participate in
meaning verification. Dropping a question mark does not silently turn a supported
question into an assertion. Mixed statement/question passages share one segmenter.

These remain bounded constructions: the noun modifiers are `great/good`, the
initial noun qualifier is `of self-harm`, named-instance syntax is `the planet
Name`, and contextual names are single words. General why/where/when questions,
embedded questions, tags, contractions, and arbitrary wh adjunct extraction
remain unsupported. Lexical/query IDs are local, not verified WordNet IDs.

## Evaluation

```python
from symbolnlp.rewording.evaluation import evaluate

report = evaluate(['Alice helps Bob.', 'It is 90 degrees outside.'], trials=64)
```

This offline, seeded evaluation reports distinct outputs, empirical output
entropy, unchanged trials, structural fidelity passes, and coverage. A caller
may supply `detector=callable` for original-versus-output detector scores; no
watermark detector or attribution model is bundled. Diversity is not proof of
signal removal. Source recognition tests with decoys, actual watermark detectors,
adversarial communication experiments, and downstream task utility evaluations
remain necessary before claiming a deployed defense.
