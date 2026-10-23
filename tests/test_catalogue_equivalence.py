"""A packaging rebuild may change measured metadata, never source or search semantics."""

import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest
from catalogue_fixtures import archive
from torob.ingest import ingest_archive


def comparison_module():
    spec = importlib.util.spec_from_file_location('compare_catalogues', Path(__file__).parents[1] / 'scripts/compare_catalogues.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pair(tmp_path):
    source = archive(tmp_path)
    before, after = tmp_path / 'before.sqlite', tmp_path / 'after.sqlite'
    ingest_archive(source, before, expected_hashes={})
    ingest_archive(source, after, expected_hashes={})
    return before, after


def test_all_rows_schema_indexes_and_manifest_equal_except_measured_duration(tmp_path):
    before, after = pair(tmp_path)
    with sqlite3.connect(after) as db:
        value = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        value['duration_seconds'] = 999
        db.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps(value),))
    result = comparison_module().compare(before, after)
    assert result['equivalent'] is True
    assert result['tables']['offers']['rows'] == 3
    assert result['tables']['product_search']['rows'] == 2
    assert result['ignored_metadata_fields'] == ['duration_seconds']
    assert result['reference_binary_sha256'] != result['candidate_binary_sha256']


@pytest.mark.parametrize('kind', ['source_field', 'exact_price', 'fts_text', 'missing_index', 'source_hash', 'unknown_metadata'])
def test_equivalence_rejects_each_material_difference_without_writing_inputs(tmp_path, kind):
    import hashlib

    before, after = pair(tmp_path)
    with sqlite3.connect(after) as db:
        if kind == 'source_field':
            db.execute("UPDATE offers SET data='{}' WHERE offer_id='o1'")
        elif kind == 'exact_price':
            db.execute("UPDATE offers SET price=101 WHERE offer_id='o1'")
        elif kind == 'fts_text':
            db.execute("UPDATE product_search SET text='wrong variant' WHERE product_id='p1'")
        elif kind == 'missing_index':
            db.execute('DROP INDEX offer_shop')
        else:
            value = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
            if kind == 'source_hash':
                value['payload_hashes']['offers.csv'] = 'untrusted'
            else:
                value['unexpected'] = 'not safe to ignore'
            db.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps(value),))
    fingerprints = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after)]
    with pytest.raises(ValueError, match='differs'):
        comparison_module().compare(before, after)
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after)] == fingerprints


def test_organizer_transport_provenance_requires_the_exact_pinned_pair_and_payloads(tmp_path):
    from torob.ingest import KNOWN_HASHES
    before, after = pair(tmp_path)
    m = comparison_module()
    with pytest.raises(ValueError, match='pinned pair'):
        m.compare(before, after, organizer_archive=True)
    hashes = ['37a25fbd4cdb30aec265d6367e7ebafd8673364ffc90e74411a5f13cd7d94013', 'b0afb47b2b70f65c6d8ec07b7423dcc49efc71cd7a27e95606fb81da008c210d']
    for path, archive_hash in zip((before, after), hashes):
        with sqlite3.connect(path) as db:
            value = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
            value.update(archive_sha256=archive_hash, payload_hashes=KNOWN_HASHES)
            db.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps(value),))
    report = m.compare(before, after, organizer_archive=True)
    assert report['equivalent'] is True
    assert report['checked_transport_provenance']['candidate_archive_sha256'] == hashes[1]
    with sqlite3.connect(after) as db:
        value = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        value['payload_hashes'] = {'bad': 'not accepted'}
        db.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps(value),))
    with pytest.raises(ValueError, match='payload hashes'):
        m.compare(before, after, organizer_archive=True)
