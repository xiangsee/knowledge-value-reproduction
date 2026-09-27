#!/usr/bin/env python3
"""Validate the public baseline structure, not research or instrument validity."""
from pathlib import Path
from hashlib import sha256
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = []
    paths = [p for p in ROOT.rglob('*') if p.is_file()
             and '.git' not in p.relative_to(ROOT).parts]
    docs = [p for p in paths if p.suffix == '.md']
    for p in paths:
        if p.suffix == '.json':
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as exc:
                errors.append(f'Invalid JSON: {p.relative_to(ROOT)}: {exc}')
        if p.suffix.lower() in {'.pdf', '.zip', '.pem', '.key'} or p.name.startswith('.env'):
            errors.append(f'Unexpected public artifact: {p.relative_to(ROOT)}')
    pattern = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)\)')
    for p in docs:
        text = p.read_text(encoding='utf-8')
        if any(value in text for value in ('sandbox:', '/Users/', '/mnt/data/')):
            errors.append(f'Local-only reference: {p.relative_to(ROOT)}')
        for link in pattern.findall(text):
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', link) or link.startswith('#'):
                continue
            target = link.split('#', 1)[0]
            if target and not (p.parent / target).exists():
                errors.append(f'Missing link: {p.relative_to(ROOT)} -> {target}')
    manifest = json.loads((ROOT / 'provenance/files.json').read_text())
    recorded = {entry['path'] for entry in manifest['files']}
    actual = {str(p.relative_to(ROOT)) for p in paths} - {'provenance/files.json'}
    if recorded != actual:
        errors.append('File inventory differs from the baseline manifest')
    for item in manifest['files']:
        p = ROOT / item['path']
        if not p.exists() or sha256(p.read_bytes()).hexdigest() != item['sha256']:
            errors.append(f'Manifest mismatch: {item["path"]}')
    exp = ROOT / 'experiments/evidence-judgment'
    forms = (exp / '03_candidate_forms.md').read_text()
    ids = re.findall(r'^### ([ABC][1-4])｜', forms, re.M)
    if len(ids) != 12 or len(set(ids)) != 12:
        errors.append('Expected 12 unique pilot items')
    if '虚构' not in forms or '公开' not in (exp / 'README.md').read_text():
        errors.append('Missing synthetic/public-exposure warning')
    template = json.loads((exp / '07_response_template.json').read_text())
    if template['record_type'] != 'blank_template_not_observation' or template['participant_id'] is not None:
        errors.append('Response template must remain blank')
    original_checks = json.loads((exp / '08_build_checks.json').read_text())
    for item in original_checks['files']:
        p = exp / item['name']
        if sha256(p.read_bytes()).hexdigest() != item['sha256']:
            errors.append(f'Pilot checksum mismatch: {item["name"]}')
    source_ids = [s['id'] for s in json.loads((ROOT / 'evidence/sources.json').read_text())['sources']]
    if len(source_ids) != len(set(source_ids)):
        errors.append('Source IDs are not unique')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(json.dumps({'status': 'pass', 'files': len(paths), 'markdown_files': len(docs),
                      'pilot_items': 12, 'source_records': len(source_ids),
                      'human_observations': 0, 'scope': 'structure_only',
                      'external_sources_rechecked': False, 'empirical_validation': False},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
