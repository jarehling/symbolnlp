"""Surface observations on original text, not a steganography detector.

Unicode confusables are a small explicit heuristic, NOT the Unicode Consortium's
complete confusables table. Findings carry offsets and escaped labels, not source
excerpts. Legitimate scripts, formatting and emphasis can trigger observations.
"""
from bisect import bisect_right
from collections import Counter
import json
import re
import unicodedata as ud

# Visually confusable candidates in common fonts; no automatic substitutions.
CONFUSABLES = dict(zip('АВЕКМНОРСТХаеорсухіјѕ', 'ABEKMHOPCTXaeopcyxijs'))
CONFUSABLES.update(dict(zip('ΑΒΕΖΗΙΚΜΝΟΡΤΥΧορι', 'ABEZHIKMNOPTYXopi')))
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x180E}
BIDI = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}
PUNCTUATION_VARIANTS = {'“': 'double_quote', '”': 'double_quote', '„': 'double_quote',
                        '‘': 'single_quote', '’': 'single_quote', '–': 'en_dash',
                        '—': 'em_dash', '…': 'ellipsis', '−': 'minus'}


def _script(char):
    name = ud.name(char, '')
    return next((script for script in ('LATIN', 'GREEK', 'CYRILLIC') if script in name), None)


def inspect_surface(text: str, *, max_positions: int = 20, max_groups: int = 200) -> dict:
    """Report heuristically detectable surface artifacts before normalization.

    Offsets are zero-based Python Unicode code-point offsets; line/column are
    one-based. Counts can overlap across findings and are not suspiciousness scores.
    """
    if not isinstance(text, str):
        raise ValueError('Surface inspection requires a string')
    if type(max_positions) is not int or max_positions < 1 or type(max_groups) is not int or max_groups < 1:
        raise ValueError('Inspection limits must be positive integers')
    line_starts = [0] + [m.end() for m in re.finditer(r'\r\n|\r|\n', text)]
    groups = {}
    omitted = 0
    category_counts = Counter()

    def emit(category, kind, offset, length=1, **details):
        nonlocal omitted
        category_counts[category] += 1
        key = (category, kind, json.dumps(details, sort_keys=True))
        if key not in groups:
            if len(groups) >= max_groups:
                omitted += 1
                return
            groups[key] = {'category': category, 'kind': kind, 'details': details,
                           'count': 0, 'positions': []}
        group = groups[key]
        group['count'] += 1
        if len(group['positions']) < max_positions:
            line = bisect_right(line_starts, offset)
            group['positions'].append({'offset': offset, 'length': length, 'line': line,
                                       'column': offset - line_starts[line - 1] + 1})

    scripts = Counter()
    for i, char in enumerate(text):
        point, category = ord(char), ud.category(char)
        name = ud.name(char, 'UNNAMED')
        script = _script(char)
        if script:
            scripts[script.lower()] += 1
        info = {'codepoint': f'U+{point:04X}', 'unicode_name': name}
        if char in CONFUSABLES:
            emit('unicode', 'possible_homoglyph', i, latin_candidate=CONFUSABLES[char], **info)
        compatibility = ud.normalize('NFKC', char)
        if compatibility != char:
            emit('unicode', 'compatibility_character', i,
                 normalized_codepoints=[f'U+{ord(c):04X}' for c in compatibility], **info)
        if point in ZERO_WIDTH or point in {0xFE0E, 0xFE0F} or 0xE0100 <= point <= 0xE01EF:
            emit('invisible', 'zero_width_or_variation_character', i, **info)
        if point in BIDI:
            emit('invisible', 'bidirectional_control', i, **info)
        if category.startswith('C') and not char.isspace():
            emit('invisible', 'control_or_format_character', i, **info)
        if char.isspace() and char not in ' \t\r\n':
            emit('whitespace', 'nonstandard_whitespace', i, **info)
        if char == '\t':
            emit('whitespace', 'tab', i)
        if char in PUNCTUATION_VARIANTS:
            emit('punctuation', 'typographic_variant', i, variant=PUNCTUATION_VARIANTS[char], **info)

    for match in re.finditer(r'[^\W\d_]+', text, re.UNICODE):
        word = match.group()
        word_scripts = sorted({s.lower() for c in word if (s := _script(c))})
        if len(word_scripts) > 1:
            emit('unicode', 'mixed_script_word', match.start(), len(word), scripts=word_scripts)
        letters = [c for c in word if c.isalpha()]
        if len(letters) > 1 and word.isupper():
            emit('capitalization', 'all_caps_word', match.start(), len(word))
        if any(c.isupper() for c in word[1:]) and not word.isupper():
            emit('capitalization', 'internal_capitals', match.start(), len(word))

    patterns = [
        ('whitespace', 'repeated_spaces', r' {2,}'),
        ('whitespace', 'trailing_line_whitespace', r'[ \t]+(?=\r?$)', re.MULTILINE),
        ('whitespace', 'leading_line_whitespace', r'^[ \t]+', re.MULTILINE),
        ('whitespace', 'repeated_blank_lines', r'\n(?:[ \t]*\r?\n){2,}'),
        ('punctuation', 'repeated_punctuation', r'[!?.,;:]{2,}'),
        ('punctuation', 'space_before_punctuation', r'[ \t]+[.,;:!?]'),
        ('punctuation', 'missing_space_after_punctuation', r'[.!?][A-Za-z]'),
        ('capitalization', 'lowercase_sentence_initial', r'(?:^\s*|[.!?]\s+)([a-z])'),
        ('markdown', 'heading', r'^ {0,3}#{1,6}(?:[ \t]+|$)', re.MULTILINE),
        ('markdown', 'bullet_marker', r'^[ \t]*([-+*])[ \t]+', re.MULTILINE),
        ('markdown', 'ordered_list_marker', r'^[ \t]*\d+[.)][ \t]+', re.MULTILINE),
        ('markdown', 'fence_marker', r'^ {0,3}(`{3,}|~{3,})', re.MULTILINE),
        ('markdown', 'inline_code_marker', r'`+'),
        ('markdown', 'emphasis_marker', r'\*{1,3}|_{1,3}'),
        ('markdown', 'link_or_image', r'!?\[[^\]\n]*\]\([^\)\n]*\)'),
        ('markdown', 'blockquote_marker', r'^ {0,3}>[ \t]?', re.MULTILINE),
        ('markdown', 'hard_line_break', r' {2,}(?=\r?$)', re.MULTILINE),
    ]
    bullet_styles = set()
    for category, kind, pattern, *flags in patterns:
        for match in re.finditer(pattern, text, flags[0] if flags else 0):
            start, end = match.span(1) if kind == 'lowercase_sentence_initial' else match.span()
            details = {}
            if kind == 'bullet_marker':
                bullet_styles.add(match.group(1))
                details['marker'] = match.group(1)
            emit(category, kind, start, end - start, **details)
    if len(bullet_styles) > 1:
        emit('markdown', 'mixed_bullet_markers', 0, 0, markers=sorted(bullet_styles))
    line_endings = Counter(m.group().encode('unicode_escape').decode('ascii') for m in re.finditer(r'\r\n|\r|\n', text))
    if len(line_endings) > 1:
        emit('whitespace', 'mixed_line_endings', 0, 0, styles=sorted(line_endings))
    findings = list(groups.values())
    for finding in findings:
        finding['positions_omitted'] = finding['count'] - len(finding['positions'])
    return {
        'method': 'stdlib_surface_heuristics_v1', 'reference': 'original_input_before_normalization',
        'detected': bool(category_counts), 'observation_count': sum(category_counts.values()),
        'category_counts': dict(sorted(category_counts.items())),
        'script_letter_counts': dict(sorted(scripts.items())), 'line_ending_counts': dict(line_endings),
        'findings': findings, 'omitted_group_occurrences': omitted,
        'offset_unit': 'Unicode code points; zero-based offsets, one-based line and column',
        'limits': {'max_positions_per_group': max_positions, 'max_groups': max_groups},
        'interpretation': 'Observations only; normal writing can trigger findings. No covert-intent or watermark inference.',
        'limitations': [
            'Homoglyph candidates use a small Greek/Cyrillic-to-Latin table, not complete Unicode confusable detection.',
            'Markdown is detected lexically, not parsed as an AST; markers inside code may also be counted.',
            'Pattern counts can overlap. Absence of findings does not establish absence of hidden signals.',
        ],
    }
