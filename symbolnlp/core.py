"""An intentionally bounded grammar; no statistical models or network calls."""
from dataclasses import asdict, dataclass
import random
import re
from .lexical import NAMED_ENTITIES, MODIFIER_CANONICAL


class UnsupportedText(ValueError):
    """Input falls outside the supported grammar."""


# Sense IDs are local, explicit meanings, not claims of WordNet equivalence.
# Each form is (base, third-person singular, past, past participle).
LEXICON = {
    "help.v.01": [("help", "helps", "helped", "helped"),
                  ("assist", "assists", "assisted", "assisted"),
                  ("aid", "aids", "aided", "aided"),
                  ("support", "supports", "supported", "supported")],
    "give.v.01": [("give", "gives", "gave", "given")],
    "cook.v.01": [("cook", "cooks", "cooked", "cooked")],
    "chase.v.01": [("chase", "chases", "chased", "chased")],
    "see.v.01": [("see", "sees", "saw", "seen")],
    "like.v.01": [("like", "likes", "liked", "liked")],
    "admire.v.01": [("admire", "admires", "admired", "admired")],
    "follow.v.01": [("follow", "follows", "followed", "followed")],
    "visit.v.01": [("visit", "visits", "visited", "visited")],
}
INTRANSITIVE = {"work.v.01": [("work", "works", "worked", "worked")],"sit.v.01": [("sit", "sits", "sat", "sat")],
                "sleep.v.01": [("sleep", "sleeps", "slept", "slept")]}
VERBS = {**LEXICON, **INTRANSITIVE}
ADJECTIVES = {"pleasing.a.01": "pleasing", "happy.a.01": "happy", "proud.a.01": "proud"}
NOMINALIZED_ADJECTIVES = {"proud", "rich", "poor", "young", "old"}
LOCATION_ADVERBS = {"outside", "inside", "indoors", "outdoors"}
FORMS = {word: (sense, forms, index) for sense, variants in VERBS.items()
         for forms in variants for index, word in enumerate(forms)}
BASES = {forms[0]: sense for sense, variants in LEXICON.items() for forms in variants}
MODALS = {"can", "could", "may", "might", "must", "should", "would"}
NUMERALS = {word: value for value, word in enumerate(
    "zero one two three four five six seven eight nine ten".split())}
DETERMINERS = {"the", "a", "an", "this", "that", "these", "those", "some"}

PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}

# Small local lexical classes until external dictionary integration.
MASS_NOUNS = {"weather", "rice", "butter", "water", "milk", "flour", "sand", "glory", "pride", "happiness", "knowledge"}
RELATIONS = {"friend.n.01": "friend", "neighbor.n.01": "neighbor", "member.n.01": "member"}
PRONOUN_FORMS = {"i": ("I", "me"), "you": ("you", "you"),
                 "he": ("he", "him"), "she": ("she", "her"),
                 "it": ("it", "it"), "we": ("we", "us"), "they": ("they", "them")}
PRONOUN_LEMMAS = {form.lower(): lemma for lemma, forms in PRONOUN_FORMS.items() for form in forms}
LOCATION_PREPOSITIONS = {"in", "on", "at"}


@dataclass(frozen=True)
class Entity:
    """A noun phrase or case-neutral pronoun; no coreference inference."""
    text: str | None = None
    number: str = "singular"
    noun: str | None = None
    determiner: str | None = None
    quantity: int | None = None
    pronoun: str | None = None
    mass: bool = False
    nominalized_adjective: str | None = None
    variable: str | None = None
    modifiers: tuple[str, ...] = ()
    qualifier_of: str | None = None
    named_instance: str | None = None

    def __post_init__(self):
        if self.variable is not None and self.variable != "answer":
            raise ValueError("Only the answer query variable is supported")
        if any(word not in MODIFIER_CANONICAL for word in self.modifiers):
            raise ValueError("Unsupported noun modifier")
        if self.qualifier_of is not None and self.qualifier_of != "self-harm":
            raise ValueError("Unsupported noun qualifier")
        if self.named_instance is not None and not re.fullmatch(r"[A-Z][a-z]+", self.named_instance):
            raise ValueError("Named instance must be a simple proper name")
        if (self.modifiers or self.qualifier_of or self.named_instance) and self.noun is None:
            raise ValueError("Noun modifiers require a noun")
        if self.nominalized_adjective is not None:
            if (self.nominalized_adjective not in NOMINALIZED_ADJECTIVES or
                self.number != "plural" or self.determiner != "the" or
                self.noun is not None or self.pronoun is not None or self.mass or self.quantity is not None):
                raise ValueError("Nominalized adjectives require the + supported adjective and plural number")
        if self.number not in {"singular", "plural"}:
            raise ValueError("Entity number must be singular or plural")
        if self.text is not None and (not isinstance(self.text, str) or not self.text.strip()):
            raise ValueError("Entity text must be nonempty when supplied")
        if self.noun is not None and (not isinstance(self.noun, str) or
                                      not re.fullmatch(r"[a-z]+", self.noun)):
            raise ValueError("Entity noun must be a lowercase singular noun lemma")
        if self.pronoun is not None:
            if self.pronoun not in PRONOUN_FORMS:
                raise ValueError("Unsupported pronoun lemma")
            if self.noun is not None or self.determiner is not None or self.quantity is not None or self.mass:
                raise ValueError("Pronouns cannot carry noun features")
            if self.number != ("plural" if self.pronoun in {"we", "they"} else "singular"):
                raise ValueError("Pronoun number does not agree")
        if type(self.mass) is not bool:
            raise ValueError("mass must be a boolean")
        if self.mass and (self.number != "singular" or self.quantity is not None or self.determiner in {"a", "an"}):
            raise ValueError("Mass nouns require singular agreement without count quantity or a/an")
        if self.text is None and self.noun is None and self.pronoun is None and self.nominalized_adjective is None and self.variable is None:
            raise ValueError("Entity requires noun or text")
        if self.quantity is not None:
            if type(self.quantity) is not int or self.quantity < 0:
                raise ValueError("Entity quantity must be a nonnegative integer")
            if self.number != ("singular" if self.quantity == 1 else "plural"):
                raise ValueError("Entity quantity must agree with number")
        if self.determiner is not None and self.determiner not in DETERMINERS:
            raise ValueError("Unsupported determiner")
        if self.determiner in {"a", "an", "this", "that"} and self.number != "singular":
            raise ValueError("Determiner requires singular number")
        if self.determiner in {"these", "those"} and self.number != "plural":
            raise ValueError("Determiner requires plural number")
        if self.quantity is not None and self.determiner is not None:
            raise ValueError("Combined determiner and quantity phrases are not supported")


def render_entity(entity: Entity, *, case: str = "subject") -> str:
    """Construct a noun phrase, retaining optional explicit surface text.

    Without text, singular count nouns default to a/an; unquantified plurals
    default to bare plurals. Articles use spelling rather than pronunciation.
    Noun inflection currently supports regular final-s plurals only.
    """
    if case not in {"subject", "object"}:
        raise ValueError("case must be subject or object")
    if entity.pronoun is not None:
        return PRONOUN_FORMS[entity.pronoun][case == "object"]
    if entity.text is not None:
        return entity.text
    if entity.nominalized_adjective is not None:
        return "the " + entity.nominalized_adjective
    if entity.variable and entity.noun is None:
        raise ValueError("Unrestricted query variables require interrogative rendering")
    noun = entity.noun
    if entity.number == "plural":
        noun += "s"
    if entity.modifiers:
        noun = " ".join(entity.modifiers) + " " + noun
    if entity.named_instance:
        noun += (" of " if entity.noun == "city" else " ") + entity.named_instance
    if entity.qualifier_of:
        noun += " of " + entity.qualifier_of
    if entity.quantity is not None:
        words = {value: word for word, value in NUMERALS.items()}
        return f"{words.get(entity.quantity, str(entity.quantity))} {noun}"
    determiner = entity.determiner
    if determiner is None and entity.number == "singular" and not entity.mass:
        determiner = "an" if noun[0] in "aeiou" else "a"
    return f"{determiner} {noun}" if determiner else noun


@dataclass(frozen=True)
class Adjunct:
    preposition: str
    entity: Entity

    def __post_init__(self):
        if self.preposition not in LOCATION_PREPOSITIONS:
            raise ValueError("Supported location prepositions: in, on, at")


@dataclass(frozen=True)
class Measurement:
    value: int
    unit: str = "degree"
    scale: str | None = None

    def __post_init__(self):
        if type(self.value) is not int or self.unit != "degree":
            raise ValueError("Temperature requires integer value and degree unit")
        if self.scale not in {None, "Celsius", "Fahrenheit"}:
            raise ValueError("Unsupported temperature scale")


@dataclass(frozen=True)
class QueryContext:
    role: str
    value: str | None = None
    start: int | None = None
    end: int | None = None

    def __post_init__(self):
        if self.role in {"location", "month"}:
            if not isinstance(self.value, str) or not re.fullmatch(r"[A-Z][a-z]+", self.value) or self.start is not None or self.end is not None:
                raise ValueError("Query context requires a simple named location/month")
            if self.role == "month" and self.value not in MONTHS:
                raise ValueError("Unknown month")
        elif self.role == "year_range":
            if type(self.start) is not int or type(self.end) is not int or not 1 <= self.start <= self.end <= 9999 or self.value is not None:
                raise ValueError("Invalid inclusive year range")
        else:
            raise ValueError("Unsupported query context")


MONTHS = set("January February March April May June July August September October November December".split())


@dataclass(frozen=True)
class Question:
    kind: str
    target: str | None = None
    wh_word: str | None = None
    contexts: tuple[QueryContext, ...] = ()

    def __post_init__(self):
        if self.kind == "polar":
            if self.target is not None or self.wh_word is not None or self.contexts:
                raise ValueError("Polar questions do not bind a wh variable")
        elif self.kind == "wh":
            if self.target not in {"agent", "patient", "description", "selection"} or self.wh_word not in {"what", "who"}:
                raise ValueError("Invalid wh query target")
            if self.contexts and self.target not in {"description", "selection"}:
                raise ValueError("Contexts currently supported for description/selection queries")
        else:
            raise ValueError("Question kind must be polar or wh")


@dataclass(frozen=True)
class Proposition:
    sense: str
    agent: Entity | None = None
    patient: Entity | None = None
    tense: str = "present"
    negated: bool = False
    modal: str | None = None
    lexical_form: str | None = None
    mood: str = "declarative"
    recipient: Entity | None = None
    adjuncts: tuple[Adjunct, ...] = ()
    subject: Entity | None = None
    related_to: Entity | None = None
    relation_determiner: str = "a"
    complement: Entity | None = None
    experiencer: Entity | None = None
    measurement: Measurement | None = None
    location_adverb: str | None = None
    question: Question | None = None

    def __post_init__(self):
        if (self.mood == "interrogative") != (self.question is not None):
            raise ValueError("Interrogatives require question semantics; other moods cannot carry a question")
        if self.sense in {"describe.v.01", "select.n.01"}:
            if (self.mood != "interrogative" or self.question.kind != "wh" or
                self.question.target != ("description" if self.sense == "describe.v.01" else "selection") or
                self.subject is None or self.question.wh_word != "what" or
                (self.sense == "select.n.01" and self.subject.variable != "answer") or
                (self.sense == "describe.v.01" and self.subject.variable is not None) or any(x is not None for x in
                (self.agent, self.patient, self.recipient, self.related_to, self.complement,
                 self.experiencer, self.measurement, self.lexical_form, self.modal, self.location_adverb)) or
                self.adjuncts or self.negated or self.tense != "present"):
                raise ValueError("Unsupported descriptive/selection question structure")
            return
        if self.question and self.question.kind == "wh":
            target = getattr(self, self.question.target, None)
            if self.question.target not in {"agent", "patient"} or target is None or target.variable != "answer":
                raise ValueError("Wh event questions require a variable in the requested role")
        for role in (self.agent, self.patient, self.subject, self.recipient, self.related_to, self.complement, self.experiencer):
            if role is not None and role.variable and (not self.question or self.question.kind != "wh" or
                                                      getattr(self, self.question.target, None) is not role):
                raise ValueError("Unbound query variable")
        if self.location_adverb is not None and self.location_adverb not in LOCATION_ADVERBS:
            raise ValueError("Unsupported location adverb")
        if self.sense not in VERBS and self.sense not in RELATIONS and self.sense not in ADJECTIVES and self.sense not in {"be.v.01", "temperature.n.01"}:
            raise ValueError(f"Unknown sense: {self.sense}")
        if self.tense not in {"present", "past", "future"}:
            raise ValueError("Tense must be present, past, or future")
        if type(self.negated) is not bool:
            raise ValueError("negated must be a boolean")
        if self.modal is not None and self.modal not in MODALS:
            raise ValueError(f"Unsupported modal: {self.modal}")
        if self.modal and self.tense != "present":
            raise ValueError("Modal propositions use present tense; modal is preserved literally")
        if self.mood not in {"declarative", "imperative", "interrogative"}:
            raise ValueError("Unsupported mood")
        if self.sense in ADJECTIVES or self.sense == "temperature.n.01":
            if self.mood not in {"declarative", "interrogative"} or any(x is not None for x in (
                self.agent, self.patient, self.recipient, self.related_to, self.complement, self.lexical_form)) or self.adjuncts:
                raise ValueError("Unsupported roles for adjectival or temperature predicate")
            if self.sense in ADJECTIVES:
                if self.subject is None or self.measurement is not None:
                    raise ValueError("Adjective requires subject and no measurement")
                if self.experiencer is not None and self.sense != "pleasing.a.01":
                    raise ValueError("Only pleasing currently supports a to-experiencer")
            elif self.subject is not None or self.measurement is None or self.experiencer is not None:
                raise ValueError("Weather temperature requires measurement and no referential subject")
            return
        if self.measurement is not None or self.experiencer is not None:
            raise ValueError("Measurement/experiencer not valid for this predicate")
        if self.sense in RELATIONS or self.sense == "be.v.01":
            if self.subject is None:
                raise ValueError("Copular predicates require subject")
            if self.sense in RELATIONS and (self.related_to is None or self.complement is not None):
                raise ValueError("Relational predicates require related_to and no complement")
            if self.sense == "be.v.01" and (self.complement is None or self.related_to is not None):
                raise ValueError("Nominal copula requires complement and no related_to")
            if any(x is not None for x in (self.agent, self.patient, self.recipient, self.lexical_form)) or self.adjuncts:
                raise ValueError("Relational predicates do not accept event roles")
            if self.mood not in {"declarative", "interrogative"} or self.relation_determiner not in {"a", "the"}:
                raise ValueError("Unsupported relational construction")
        else:
            if self.subject is not None or self.related_to is not None or self.complement is not None:
                raise ValueError("Events do not accept relational roles")
            if self.sense in INTRANSITIVE:
                if self.agent is None or self.patient is not None:
                    raise ValueError("Intransitive events require agent and no patient")
            elif self.patient is None:
                raise ValueError("Transitive events require patient")
            if self.recipient is not None and self.sense != "give.v.01":
                raise ValueError("Recipient currently supported only for give")
            if self.mood == "imperative" and (self.agent != _pronoun("you") or self.tense != "present" or self.modal):
                raise ValueError("Imperatives require implicit you, present tense, and no modal")
            if self.lexical_form and self.lexical_form not in {v[0] for v in VERBS[self.sense]}:
                raise ValueError("lexical_form does not belong to sense")


@dataclass(frozen=True)
class Document:
    propositions: tuple[Proposition, ...]

    def __post_init__(self):
        if not 1 <= len(self.propositions) <= 3:
            raise ValueError("Expected one to three propositions")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        propositions = []
        for record in data["propositions"]:
            fields = dict(record)
            for role in ("agent", "patient", "recipient", "subject", "related_to", "complement", "experiencer"):
                if fields.get(role) is not None:
                    fields[role] = Entity(**{**fields[role], "modifiers": tuple(fields[role].get("modifiers", ()))})
            if fields.get("question") is not None:
                q = dict(fields["question"])
                q["contexts"] = tuple(QueryContext(**context) for context in q.get("contexts", ()))
                fields["question"] = Question(**q)
            if fields.get("measurement") is not None:
                fields["measurement"] = Measurement(**fields["measurement"])
            fields["adjuncts"] = tuple(Adjunct(a["preposition"], Entity(**{**a["entity"], "modifiers": tuple(a["entity"].get("modifiers", ())) }))
                                      for a in fields.get("adjuncts", ()))
            propositions.append(Proposition(**fields))
        return cls(tuple(propositions))


def _pronoun(lemma):
    return Entity(pronoun=lemma, number="plural" if lemma in {"we", "they"} else "singular")


def _third_singular(entity):
    return entity.number == "singular" and entity.pronoun not in {"i", "you"}


def _be(entity, tense):
    if tense == "past":
        return "were" if entity.number == "plural" or entity.pronoun == "you" else "was"
    if entity.pronoun == "i":
        return "am"
    return "is" if _third_singular(entity) else "are"



def _entity(tokens):
    if not tokens:
        raise UnsupportedText("Missing noun phrase")
    lowered = [t.lower() for t in tokens]
    if len(tokens) == 1 and lowered[0] in PRONOUN_LEMMAS:
        return _pronoun(PRONOUN_LEMMAS[lowered[0]])
    if len(tokens) >= 3 and lowered[-2:] == ["of", "self-harm"]:
        from dataclasses import replace
        return replace(_entity(tokens[:-2]), text=None, qualifier_of="self-harm")
    if len(tokens) == 3 and lowered[0] == "the" and lowered[1] == "planet" and tokens[2][0].isupper():
        return Entity(noun="planet", determiner="the", named_instance=tokens[2])
    if len(tokens) >= 3 and lowered[0] in DETERMINERS and lowered[1] in MODIFIER_CANONICAL:
        from dataclasses import replace
        return replace(_entity([tokens[0]] + tokens[2:]), text=None, modifiers=(MODIFIER_CANONICAL[lowered[1]],))
    if len(tokens) == 1 and tokens[0] in NAMED_ENTITIES:
        return Entity(noun=NAMED_ENTITIES[tokens[0]], named_instance=tokens[0], determiner="the")
    if len(tokens) == 4 and lowered[:3] == ["the", "city", "of"] and NAMED_ENTITIES.get(tokens[3]) == "city":
        return Entity(noun="city", named_instance=tokens[3], determiner="the")
    if any(t in PRONOUNS for t in lowered):
        raise UnsupportedText("Unsupported compound pronoun phrase")
    if any(t in {"and", "or", "who", "which", "by", "not", "if", "because", "to", "of", "in", "on", "at"}
           or t in FORMS or t in MODALS or t in {"is", "are", "was", "were", "will", "do", "does", "did"}
           for t in lowered):
        raise UnsupportedText("Complex noun phrases and embedded clauses are not supported")

    def noun_features(noun):
        if not noun.isalpha() or noun in DETERMINERS or noun in NUMERALS:
            raise UnsupportedText("Expected a simple noun")
        plural = noun.endswith("s") and not noun.endswith(("ss", "us", "is"))
        # Regular -s plurals only: richer morphology needs a noun lexicon.
        return (noun[:-1] if plural else noun), ("plural" if plural else "singular")

    if len(tokens) == 1:
        if lowered[0] in MASS_NOUNS:
            return Entity(noun=lowered[0], mass=True)
        noun, number = noun_features(lowered[0])
        if number == "plural":
            return Entity(lowered[0], number, noun=noun)
        if tokens[0][0].isupper():
            return Entity(tokens[0])
    if len(tokens) == 2:
        head, surface_noun = lowered
        if head == "the" and surface_noun in NOMINALIZED_ADJECTIVES:
            return Entity(number="plural", determiner="the", nominalized_adjective=surface_noun)
        noun, number = noun_features(surface_noun)
        if head in DETERMINERS:
            required = ("singular" if head in {"a", "an", "this", "that"} else
                        "plural" if head in {"these", "those"} else None)
            if required and number != required:
                raise UnsupportedText("Determiner does not agree with noun number")
            return Entity(" ".join(lowered), number, noun=noun, determiner=head, mass=noun in MASS_NOUNS)
        quantity = NUMERALS.get(head)
        if head.isascii() and head.isdecimal():
            quantity = int(head)
        if quantity is not None:
            if number != ("singular" if quantity == 1 else "plural"):
                raise UnsupportedText("Numeral does not agree with noun number")
            return Entity(" ".join(lowered), number, noun=noun, quantity=quantity, mass=noun in MASS_NOUNS)
    raise UnsupportedText("Use a proper name, bare plural, or determiner/numeral plus noun")


def _case_entity(tokens, case):
    entity = _entity(tokens)
    if entity.pronoun and tokens[0].lower() != PRONOUN_FORMS[entity.pronoun][case == "object"].lower():
        raise UnsupportedText(f"Expected {case} pronoun case")
    return entity


def _split_np(tokens):
    """Consume one bounded noun phrase (for double-object give)."""
    if not tokens:
        raise UnsupportedText("Missing recipient")
    head = tokens[0].lower()
    size = 2 if head in DETERMINERS or head in NUMERALS or head.isdecimal() else 1
    return _case_entity(tokens[:size], "object"), tokens[size:]


def _special_copula(tokens):
    """Recognize bounded adjective predicates and ambient temperatures."""
    lower = [t.lower() for t in tokens]
    j = next((i for i, t in enumerate(lower) if t in {"am", "is", "are", "was", "were", "will"} | MODALS), None)
    if j is None:
        return None
    end = j + 1
    while end < len(tokens) and lower[end] in {"not", "be"}:
        end += 1
    remaining = tokens[end:]
    if not remaining:
        return None
    adjective_sense = next((s for s, word in ADJECTIVES.items() if remaining[0].lower() == word), None)
    temperature = re.fullmatch(r"-?[0-9]+", remaining[0]) is not None
    if adjective_sense is None and not temperature:
        return None
    subject = _case_entity(tokens[:j], "subject")
    aux = lower[j:end]
    negated = "not" in aux
    modal = aux[0] if aux[0] in MODALS else None
    tense = "future" if aux[0] == "will" else "past" if aux[0] in {"was", "were"} else "present"
    expected = [modal or "will", "be"] if modal or tense == "future" else [_be(subject, tense)]
    expected = expected[:1] + (["not"] if negated else []) + expected[1:]
    if aux != expected:
        raise UnsupportedText("Copula does not agree with subject")
    location = None
    if remaining[-1].lower() in LOCATION_ADVERBS:
        location = remaining.pop().lower()
    if adjective_sense:
        experiencer = None
        if len(remaining) > 1:
            if adjective_sense != "pleasing.a.01" or remaining[1].lower() != "to":
                raise UnsupportedText("Unsupported adjective complement")
            experiencer = _case_entity(remaining[2:], "object")
        return Proposition(adjective_sense, subject=subject, experiencer=experiencer,
                           tense=tense, negated=negated, modal=modal, location_adverb=location)
    if subject.pronoun != "it" or len(remaining) not in {2, 3}:
        raise UnsupportedText("Ambient temperature requires expletive it and degree measurement")
    value = int(remaining[0])
    if remaining[1].lower() != ("degree" if value == 1 else "degrees"):
        raise UnsupportedText("Temperature unit must agree with value")
    scale = remaining[2].capitalize() if len(remaining) == 3 else None
    return Proposition("temperature.n.01", measurement=Measurement(value, scale=scale),
                       tense=tense, negated=negated, modal=modal, location_adverb=location)


def _parse_sentence(sentence, normalize):
    from .questions import parse_information_request
    request = parse_information_request(sentence, normalize)
    if request is not None:
        return request
    if "," in sentence:
        if sentence.count(",") != 1:
            raise UnsupportedText("Only one fronted location phrase is supported")
        front, clause = (part.strip() for part in sentence.split(","))
        parts = front.split()
        if not parts or parts[0].lower() not in LOCATION_PREPOSITIONS:
            raise UnsupportedText("Comma must separate a fronted location phrase")
        location = Adjunct(parts[0].lower(), _case_entity(parts[1:], "object"))
        proposition = _parse_sentence(clause, normalize)
        if proposition.sense not in VERBS:
            raise UnsupportedText("Fronted locations currently modify events only")
        from dataclasses import replace
        return replace(proposition, adjuncts=(location,) + proposition.adjuncts)
    tokens = sentence.split()
    lower = [t.lower() for t in tokens]
    special = _special_copula(tokens)
    if special is not None:
        return special
    # Copular relational nouns are semantic predicates, not action agents/patients.
    relation_index = next((i for i, t in enumerate(lower) if t in RELATIONS.values()), None)
    if relation_index is not None and "of" in lower and not any(t in FORMS for t in lower):
        j = next((i for i, t in enumerate(lower) if t in {"am", "is", "are", "was", "were", "will"} | MODALS), None)
        if j is None:
            raise UnsupportedText("Expected copula before relational noun")
        subject = _case_entity(tokens[:j], "subject")
        aux = lower[j:relation_index - 1]
        determiner = lower[relation_index - 1]
        negated = "not" in aux
        positive = [t for t in aux if t != "not"]
        modal = positive[0] if positive and positive[0] in MODALS else None
        tense = "future" if positive and positive[0] == "will" else "past" if positive and positive[0] in {"was", "were"} else "present"
        expected = [modal or "will", "be"] if modal or tense == "future" else [_be(subject, tense)]
        expected = expected[:1] + (["not"] if negated else []) + expected[1:]
        if aux != expected or determiner not in {"a", "the"} or lower[relation_index + 1:relation_index + 2] != ["of"]:
            raise UnsupportedText("Expected agreeing copula + a/the + relational noun + of + entity")
        related = _case_entity(tokens[relation_index + 2:], "object")
        sense = next(s for s, noun in RELATIONS.items() if noun == lower[relation_index])
        return Proposition(sense, tense=tense, negated=negated, modal=modal,
                           subject=subject, related_to=related, relation_determiner=determiner)

    if not any(t in FORMS for t in lower):
        j = next((i for i, t in enumerate(lower) if t in {"am", "is", "are", "was", "were", "will"} | MODALS), None)
        if j is not None:
            subject = _case_entity(tokens[:j], "subject")
            end = j + 1
            while end < len(tokens) and lower[end] in {"not", "be"}:
                end += 1
            aux = lower[j:end]
            negated = "not" in aux
            modal = aux[0] if aux[0] in MODALS else None
            tense = "future" if aux[0] == "will" else "past" if aux[0] in {"was", "were"} else "present"
            expected = [modal or "will", "be"] if modal or tense == "future" else [_be(subject, tense)]
            expected = expected[:1] + (["not"] if negated else []) + expected[1:]
            if aux != expected:
                raise UnsupportedText("Copula does not agree with subject")
            return Proposition("be.v.01", subject=subject, complement=_case_entity(tokens[end:], "object"),
                               tense=tense, negated=negated, modal=modal)

    candidates = [i for i, t in enumerate(lower) if t in FORMS]
    if len(candidates) != 1:
        raise UnsupportedText("Expected exactly one known verb or relational predicate per sentence")
    i = candidates[0]
    sense, forms, _ = FORMS[lower[i]]
    before, after = tokens[:i], tokens[i + 1:]
    location_adverb = None
    if after and after[-1].lower() in LOCATION_ADVERBS:
        location_adverb = after[-1].lower()
        after = after[:-1]
    # Extract bounded event locations without guessing instruments or agent identities.
    adjuncts = []
    location_start = next((k for k, t in enumerate(after) if t.lower() in LOCATION_PREPOSITIONS), len(after))
    tail, after = after[location_start:], after[:location_start]
    while tail:
        prep = tail[0].lower()
        end = next((k for k in range(1, len(tail)) if tail[k].lower() in LOCATION_PREPOSITIONS), len(tail))
        adjuncts.append(Adjunct(prep, _case_entity(tail[1:end], "object")))
        tail = tail[end:]
    imperative = not before or [t.lower() for t in before] == ["do", "not"]
    auxiliaries = {"do", "does", "did", "am", "is", "are", "was", "were", "will", "be", "not"} | MODALS
    j = next((k for k, t in enumerate(before) if t.lower() in auxiliaries), len(before))
    subject = _pronoun("you") if imperative else _case_entity(before[:j], "subject")
    aux = [t.lower() for t in before[j:]]
    negative = "not" in aux
    positive_aux = [t for t in aux if t != "not"]
    modal = positive_aux[0] if positive_aux and positive_aux[0] in MODALS else None
    tense = "past" if positive_aux and positive_aux[0] in {"did", "was", "were"} else "present"
    if positive_aux and positive_aux[0] == "will":
        tense = "future"
    passive = positive_aux in [["am"], ["is"], ["are"], ["was"], ["were"], ["will", "be"]] or (modal and positive_aux == [modal, "be"])
    recipient = None
    if passive:
        if sense in INTRANSITIVE:
            raise UnsupportedText("Intransitive verbs cannot be passive")
        expected_aux = [modal or "will", "be"] if modal or tense == "future" else [_be(subject, tense)]
        expected = expected_aux[:1] + (["not"] if negative else []) + expected_aux[1:]
        if aux != expected or lower[i] != forms[3]:
            raise UnsupportedText("Expected agreeing passive auxiliary and participle")
        patient, agent = subject, None
        by = next((k for k, t in enumerate(after) if t.lower() == "by"), len(after))
        if by < len(after):
            agent = _case_entity(after[by + 1:], "object")
        remaining = after[:by]
        if remaining:
            if sense != "give.v.01" or remaining[0].lower() != "to":
                raise UnsupportedText("Unsupported passive complement")
            recipient = _case_entity(remaining[1:], "object")
    else:
        agent = subject
        if sense in INTRANSITIVE:
            if after:
                raise UnsupportedText("Intransitive verb does not accept an object")
            patient = None
        elif sense == "give.v.01":
            to = next((k for k, t in enumerate(after) if t.lower() == "to"), None)
            if to is not None:
                patient = _case_entity(after[:to], "object")
                recipient = _case_entity(after[to + 1:], "object")
            else:
                first, rest = _split_np(after)
                if rest:
                    recipient, patient = first, _case_entity(rest, "object")
                else:
                    patient = first
        else:
            patient = _case_entity(after, "object")
        if imperative:
            if lower[i] != forms[0]:
                raise UnsupportedText("Imperatives require a base verb")
        elif not aux:
            if lower[i] == forms[2]:
                tense = "past"
            elif lower[i] != forms[1 if _third_singular(subject) else 0]:
                raise UnsupportedText("Verb does not agree with subject")
        else:
            head = modal or ("will" if tense == "future" else "did" if tense == "past" else "does" if _third_singular(subject) else "do")
            if aux != [head] + (["not"] if negative else []) or lower[i] != forms[0]:
                raise UnsupportedText("Unsupported auxiliary or inflection")
            if not negative and head in {"do", "does", "did"}:
                raise UnsupportedText("Emphatic do is not represented")
    return Proposition(sense, agent, patient, tense, negative, modal,
                       None if normalize else forms[0], mood="imperative" if imperative else "declarative",
                       recipient=recipient, adjuncts=tuple(adjuncts), location_adverb=location_adverb)


def split_sentences(text: str) -> list[str]:
    """Shared segmentation preserving declarative vs interrogative terminators."""
    if not isinstance(text, str) or not text.strip():
        raise UnsupportedText("Text must be nonempty")
    pieces = re.findall(r"[^.?]+[.?]?|[.?]", text.strip())
    sentences = [piece.strip() for piece in pieces]
    if any(not sentence or sentence in {".", "?"} for sentence in sentences):
        raise UnsupportedText("Empty sentence or repeated terminators")
    return [s if s.endswith((".", "?")) else s + "." for s in sentences]


def parse(text: str, *, normalize: bool = True) -> Document:
    """Parse one to three controlled sentences, including supported interrogatives."""
    if not isinstance(text, str) or not text.strip():
        raise UnsupportedText("Text must be nonempty")
    if not re.fullmatch(r"[A-Za-z0-9 .,?\-]+", text):
        raise UnsupportedText("Only words, integers, periods, question marks, hyphens, and fronting commas are supported")
    sentences = split_sentences(text)
    if not 1 <= len(sentences) <= 3:
        raise UnsupportedText("Expected one to three sentences")
    from .questions import parse_question
    return Document(tuple(parse_question(s[:-1], normalize) if s.endswith("?")
                          else _parse_sentence(s[:-1], normalize) for s in sentences))


def render(document: Document, *, vocabulary: str = "canonical", structure: str = "active",
           seed: int | None = None) -> str:
    """Realize propositions; random choices are reproducible with a seed.

    vocabulary: canonical | preserve | random; structure: active | passive | random.
    """
    if vocabulary not in {"canonical", "preserve", "random"}:
        raise ValueError("Invalid vocabulary option")
    if structure not in {"active", "passive", "random"}:
        raise ValueError("Invalid structure option")
    rng = random.Random(seed)
    sentences = []
    for p in document.propositions:
        if p.question is not None:
            from .questions import render_question
            sentences.append(render_question(p, vocabulary=vocabulary, structure=structure, seed=seed))
            continue
        neg = " not" if p.negated else ""
        if p.sense in ADJECTIVES or p.sense == "temperature.n.01":
            subject = p.subject if p.subject is not None else _pronoun("it")
            copula = ((p.modal or "will") + neg + " be" if p.modal or p.tense == "future"
                      else _be(subject, p.tense) + neg)
            if p.sense in ADJECTIVES:
                predicate = ADJECTIVES[p.sense]
                if p.experiencer is not None:
                    predicate += " to " + render_entity(p.experiencer, case="object")
            else:
                m = p.measurement
                predicate = f"{m.value} {'degree' if m.value == 1 else 'degrees'}"
                if m.scale:
                    predicate += " " + m.scale
            sentence = f"{render_entity(subject)} {copula} {predicate}"
        elif p.sense in RELATIONS or p.sense == "be.v.01":
            if p.modal or p.tense == "future":
                copula = (p.modal or "will") + neg + " be"
            else:
                copula = _be(p.subject, p.tense) + neg
            if p.sense == "be.v.01":
                sentence = f"{render_entity(p.subject)} {copula} {render_entity(p.complement, case='object')}"
            else:
                sentence = (f"{render_entity(p.subject)} {copula} {p.relation_determiner} "
                            f"{RELATIONS[p.sense]} of {render_entity(p.related_to, case='object')}")
        else:
            variants = VERBS[p.sense]
            forms = rng.choice(variants) if vocabulary == "random" else next(
                (v for v in variants if vocabulary == "preserve" and v[0] == p.lexical_form), variants[0])
            voice = rng.choice(["active", "passive"]) if structure == "random" else structure
            if p.mood == "imperative" or p.sense in INTRANSITIVE:
                voice = "active"
            elif p.agent is None:
                voice = "passive"
            subject, obj = (p.agent, p.patient) if voice == "active" else (p.patient, p.agent)
            if p.mood == "imperative":
                verb = ("do not " if p.negated else "") + forms[0]
            elif voice == "passive":
                aux = p.modal or ("will" if p.tense == "future" else _be(subject, p.tense))
                verb = aux + neg + (" be" if p.modal or p.tense == "future" else "") + " " + forms[3]
            elif p.modal or p.tense == "future":
                verb = (p.modal or "will") + neg + " " + forms[0]
            elif p.negated:
                verb = ("did" if p.tense == "past" else "does" if _third_singular(subject) else "do") + neg + " " + forms[0]
            else:
                verb = forms[2] if p.tense == "past" else forms[1 if _third_singular(subject) else 0]
            prefix = "" if p.mood == "imperative" else render_entity(subject) + " "
            if voice == "active":
                sentence = prefix + verb + (" " + render_entity(obj, case="object") if obj is not None else "")
            else:
                sentence = prefix + verb
            if p.recipient:
                sentence += " to " + render_entity(p.recipient, case="object")
            if voice == "passive" and obj is not None:
                sentence += " by " + render_entity(obj, case="object")
            for adjunct in p.adjuncts:
                sentence += " " + adjunct.preposition + " " + render_entity(adjunct.entity, case="object")
        if p.location_adverb:
            sentence += " " + p.location_adverb
        sentences.append(sentence[0].upper() + sentence[1:] + ".")
    return " ".join(sentences)
