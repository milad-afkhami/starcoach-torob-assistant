"""Read-only full semantic comparison of a catalogue rebuild; never dumps private rows."""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

TABLE_KEYS = {'shops': 'shop_id', 'products': 'product_id', 'offers': 'offer_id', 'product_search': 'product_id'}


def digest(path):
    with path.open('rb') as incoming:
        return hashlib.file_digest(incoming, 'sha256').hexdigest()


def signature(path: Path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise ValueError('Catalogue integrity differs from required ok state')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Catalogue foreign key integrity differs')
        schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        tables = {}
        for table, key in TABLE_KEYS.items():
            checksum, count = hashlib.sha256(), 0
            for row in db.execute(f'SELECT * FROM {table} ORDER BY {key}'):
                checksum.update(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode() + b'\n')
                count += 1
            tables[table] = {'rows': count, 'all_column_sha256': checksum.hexdigest()}
        metadata = {}
        for key, value in db.execute('SELECT key,value FROM metadata ORDER BY key'):
            if key == 'manifest':
                value = json.loads(value)
                value.pop('duration_seconds', None)
            metadata[key] = value
        return {'schema': schema, 'tables': tables, 'metadata': metadata}


def compare(reference: Path, candidate: Path):
    before, after = signature(reference), signature(candidate)
    if before['schema'] != after['schema']:
        raise ValueError('Catalogue schema/index set differs')
    for table in TABLE_KEYS:
        if before['tables'][table] != after['tables'][table]:
            raise ValueError(f'Catalogue table {table} differs')
    if before['metadata'] != after['metadata']:
        raise ValueError('Catalogue source metadata differs')
    return {
        'equivalent': True,
        'reference_binary_sha256': digest(reference), 'candidate_binary_sha256': digest(candidate),
        'reference_bytes': reference.stat().st_size, 'candidate_bytes': candidate.stat().st_size,
        'tables': before['tables'], 'schema': before['schema'], 'metadata': before['metadata'],
        'ignored_metadata_fields': ['duration_seconds'],
        'canonical_encoding': 'UTF-8 JSON arrays of every SQL column, ordered by exact primary source ID, one LF per row',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('equivalent', 'reference_binary_sha256', 'candidate_binary_sha256', 'tables')}, indent=2))
