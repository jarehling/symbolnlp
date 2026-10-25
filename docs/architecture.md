# Rewording architecture

## Goal and boundary

The application boundary is now `paraphrase(text) -> ParaphraseResult`, containing
`status`, optional `text`, and an audit `report`. Parsing and realization are
internal mechanisms rather than the product's main purpose. Existing parse/render
APIs remain useful for debugging and concept authoring.

The target setting is a source agent communicating through a trusted rewriting
boundary to a receiving agent or monitor. The rewriter receives source text as
data; it never executes embedded instructions or invokes a model. Reports are
separate audit material and must not become an alternate source-to-receiver
channel. Selection must occur on a host where the source cannot inspect the OS
random generator. Python's SystemRandom alone does not enforce host isolation.

## Modules

- `rewording/artifacts.py`: pre-normalization surface findings, including on
  unsupported input; bounded positions and explicit heuristic limitations.
- `rewording/canonical.py`: conservative normalization and change audit.
- `rewording/backend.py`: `RewriteBackend` protocol and symbolic sentence-space
  enumeration. Each variant has surface text and choice labels.
- `rewording/realizations.py`: bounded named-phrase, information-request, and
  modifier lexical variation over explicit equivalence classes.
- `lexical.py`: local named-entity type registry and modifier synonym classes.
- `rewording/semantics.py`: inspectable proposition-field fidelity comparison.
- `rewording/pipeline.py`: coverage, passage-space counting, private sampling,
  independent final verification, diagnostics, and result schema.
- `rewording/evaluation.py`: repeatable diversity/utility evaluation and an
  optional user-supplied detector hook.
- `alternations/catalog.py`: all 45 bounded rule families and explicit guards.
- `alternations/engine.py`: deduplicated derivation graphs and replay verification.
- `alternations/mixed.py`: ordered composition of grammar/core units, with shared
  document spelling.
- `core.py`: controlled grammar, shared statement/question segmentation, and
  semantic records including Question and QueryContext.
- `questions.py`: interrogative syntax, explicit query-variable binding,
  polar inversion, and question realization; no answering/retrieval.

The backend protocol currently returns the existing Proposition representation;
it is not a plug-and-play general-language paraphraser interface. Supporting a
new representation requires corresponding decoder/verifier changes. Final
verification deliberately decodes against original source sentences rather than
trusting a backend's own source records. A candidate with extra propositions,
changed roles, or altered negation is rejected.

## Counting and selection

Within a sentence, generate combinations of lexical lemma, legal voice,
location position, and recipient structure. Reparse, compare encoded semantics,
and deduplicate exact surface strings. Count this accepted set, not the naive
product of axes. Parameters can have dependencies.

Across sentences, preserve sentence order and use the Cartesian product of
accepted sets. The full passage count is exact for those sets. An integer rank
identifies a product element using mixed-radix decomposition. Uniformly draw
unique ranks, then uniformly select one of those candidates. Each rendering has
the same marginal selection probability. Candidate sampling uses secure
randomness by default and a clearly labeled test seed when requested.

Not excluding the input is intentional: for a common candidate lattice, excluding
the source wording gives each possible source a different output distribution.
Lexical and voice choices can instead be resampled from a shared lattice.
This argument is restricted to the encoded equivalence class; it is not a
proof against semantic or adversarial channels in general language.

## Comparison with the supplied design

Implemented: conservative canonicalization; symbolic regenerate-from-meaning;
multiple lexical and syntactic realizations; exact structural filtering; private
selection; variation counts; fidelity and surface-change reports; evaluation
scaffolding. The candidate count defaults to 16, with no source-likelihood or
disruption-based ranking. Ranking and overlap heuristics can correlate with
input wording and should be evaluated before introduction.

Deferred: model-based paraphrasers, bidirectional NLI, learned style neutralizers,
markdown AST normalization, code-specific rewriting, arbitrary Unicode
confusables, commutative claim reordering, compression/expansion, and integrated
watermark detectors. The existing non-LLM requirement remains in force. Adding
an NLI model should be optional, explicitly configured, and independently tested.
External lexical resources (WordNet and supplementary Wiktionary data) remain a
separate migration; no IDs have been falsely relabeled as verified resource IDs.

## Evaluation requirements for a stronger claim

1. Build held-out paraphrase pairs with independent human judgments; cover
   negation, scope, numbers, names, discourse, commands, register, and modality.
2. Measure downstream monitor/task performance before and after rewriting.
3. Test known watermark schemes with their actual detectors and specified
   thresholds, reporting utility alongside detection statistics.
4. Measure source recognition with decoys and held-out sources; report AUROC
   rather than treating the model's verbal self-assessment as a reliable label.
5. Exercise adaptive source/receiver pairs and measure recovered messages on
   held-out trials, including semantic, sentence-order, and length channels.
6. Test distribution equality across alternate source wordings for the same
   encoded meaning. Existing unit tests cover this on the controlled vocabulary.

The bundled evaluation measures only coverage, structural utility, diversity,
and optional external detector score changes. It does not mark watermark
removal as established even when output diversity is high. A detector's score
change is not automatically a calibrated significance result.
