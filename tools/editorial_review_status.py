"""Read authored review evidence; byte/ID checks do not certify editorial quality."""
import hashlib
import json
from pathlib import Path


def recorded_review_count(glossary, draft):
    path = glossary / 'editorial-audits.json'
    if not path.is_file():
        return 0
    record = json.loads(path.read_text())
    if record.get('standard') != 'standard-localization':
        return 0
    names = ('source-draft.json', 'entry-evidence.json',
             'roster-review.json', 'owner-decisions.json')
    current = {name: (glossary / name).read_bytes() for name in names}
    source_hash = hashlib.sha256(current['source-draft.json']).hexdigest()
    ids = [entry['id'] for entry in draft]
    count = 0
    for review in reversed(record.get('passes', [])):
        directory = Path(review.get('immutableInputDirectory', ''))
        if not directory.is_absolute():
            directory = glossary.parent / directory
        if (review.get('status') != 'complete-clean'
                or review.get('cleanFullAudit') is not True
                or review.get('findings')
                or review.get('inputSourceDraftRawSha256') != source_hash
                or review.get('reviewedEntryIds') != ids
                or not {'term', 'meaning'} <= set(review.get('fieldsRead', []))):
            break
        if not all((directory / name).is_file()
                   and (directory / name).read_bytes() == data
                   for name, data in current.items()):
            break
        count += 1
    return count
