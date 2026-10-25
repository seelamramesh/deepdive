"""Conservative, offline numeric sentence-to-passage citation checks.

Numeric presence is necessary, not proof of semantic entailment. No arithmetic,
paraphrase, causal attribution or general language understanding is inferred.
"""
import re
from decimal import Decimal

CITATION = re.compile(r"\[(?:claim|evidence):\w+\]")
END = re.compile(r"[.!?](?:[\"')])?(?:\s*\[(?:claim|evidence):\w+\])*\s+(?!\[(?:claim|evidence):)(?=\S)")
NUMBER = re.compile(r"(?<![\w])(?P<currency>[$€£])?\s*(?P<value>[+-]?\d+(?:,\d{3})*(?:\.\d+)?)(?P<unit>\s*(?:percentage\s+points?|basis\s+points?|percent(?:age)?|%))?", re.I)


def sentences(line):
    start = 0
    for match in END.finditer(line):
        prefix = line[:match.start()+1]
        if re.search(r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)|(?:\b[A-Za-z]\.)+[A-Za-z])\.$", prefix, re.I):
            continue
        yield line[start:match.end()].strip()
        start = match.end()
    if line[start:].strip():
        yield line[start:].strip()


def numeric_mentions(text):
    text = CITATION.sub("", text)
    text = re.sub(r"^\s*(?:#{1,6}\s*)?(?:[-*]\s+|\d+[.)]\s+)?", "", text)
    result = set()
    for match in NUMBER.finditer(text):
        value = str(Decimal(match['value'].replace(',', '')).normalize())
        unit = (match['unit'] or '').strip().casefold()
        if unit in {'%', 'percent', 'percentage'}: unit = '%'
        elif unit.startswith('percentage'): unit = 'percentage_points'
        elif unit.startswith('basis'): unit = 'basis_points'
        result.add((value, match['currency'] or unit))
    return result


def numeric_citation_issues(line, evidence_by_id, allowed_links):
    issues = []
    for sentence in sentences(line):
        numbers = numeric_mentions(sentence)
        if not numbers:
            continue
        claims = set(re.findall(r"\[claim:(\w+)\]", sentence))
        evidence_ids = set(re.findall(r"\[evidence:(\w+)\]", sentence))
        if not claims or not evidence_ids:
            issues.append({'reason':'numeric_sentence_missing_local_citations','sentence':sentence})
            continue
        if any(not any((cid,eid) in allowed_links for cid in claims) for eid in evidence_ids):
            issues.append({'reason':'numeric_sentence_unapproved_local_link','sentence':sentence})
            continue
        cited = set()
        for eid in evidence_ids:
            if eid in evidence_by_id:
                cited.update(numeric_mentions(evidence_by_id[eid].passage))
        missing = [(value,unit) for value,unit in numbers if not any(
            value==other and (not unit or unit==other_unit) for other,other_unit in cited)]
        if missing:
            issues.append({'reason':'number_absent_from_local_cited_passages','sentence':sentence,'missing_numbers':missing})
    return issues
