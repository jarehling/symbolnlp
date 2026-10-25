"""Small explicit equivalence classes, pending external lexical integration.

Named-entity types are curated facts, never guessed from capitalization.
Modifier synonyms are local sense assumptions, not verified WordNet mappings.
"""
NAMED_ENTITIES = {'Chicago': 'city', 'Venus': 'planet'}
MODIFIER_VARIANTS = {'great': ('great', 'outstanding'), 'good': ('good',)}
MODIFIER_CANONICAL = {word: canonical for canonical, words in MODIFIER_VARIANTS.items() for word in words}
INFORMATION_NOUNS = {'novel', 'book'}


def named_phrase(name, *, descriptive):
    if not descriptive:
        return name
    kind = NAMED_ENTITIES[name]
    return f'the {kind}{" of" if kind == "city" else ""} {name}'
