import contextlib
from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'ops/bootstrap_math_rag.py'


def load_helper():
    assert SCRIPT.is_file(), 'The math RAG bootstrap helper is missing'
    spec = importlib.util.spec_from_file_location('bootstrap_math_rag', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MathRagBootstrapTests(unittest.TestCase):
    def test_ingest_payload_routes_each_document_through_metadata_collection(self):
        helper = load_helper()
        collections = set()
        for source in helper.SOURCES:
            payload = helper.make_payload(source, '/data/uploads/maths/source.md', 'a' * 64)
            collections.add(payload['hints']['collection'])
            self.assertEqual(payload['source_type'], 'markdown')
            self.assertEqual(payload['hints']['collection'], source.collection)
            self.assertEqual(payload['hints']['source_uri'], source.url)
            self.assertEqual(payload['hints']['source_sha256'], 'a' * 64)
            self.assertEqual(payload['hints']['matiere'], 'Mathématiques')
            self.assertNotIn('collection', payload)
        self.assertEqual(collections, {'rag_maths_3e_dnb', 'rag_maths_premiere'})

    def test_rejects_nsi_and_other_unapproved_collection_targets(self):
        helper = load_helper()
        source = replace(helper.SOURCES[0], collection='nsi_corpus')
        with self.assertRaisesRegex(ValueError, 'collection'):
            helper.make_payload(source, '/data/uploads/maths/source.md', 'a' * 64)

    def test_default_dry_plan_never_downloads_or_posts(self):
        helper = load_helper()
        output = io.StringIO()
        with patch.object(helper, 'prepare_sources', side_effect=AssertionError('download')), \
             patch.object(helper, 'apply_sources', side_effect=AssertionError('mutation')), \
             contextlib.redirect_stdout(output):
            self.assertEqual(helper.main([]), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan['mode'], 'plan')
        self.assertEqual(len(plan['sources']), 4)
        self.assertEqual(set(plan['collections']), {'rag_maths_3e_dnb', 'rag_maths_premiere'})

    def test_cycle4_extracts_only_the_verified_mathematics_pages(self):
        helper = load_helper()
        cycle4 = next(s for s in helper.SOURCES if s.id == 'cycle4-2020-maths')
        self.assertEqual((cycle4.first_page, cycle4.last_page), (126, 138))
        self.assertEqual(cycle4.collection, 'rag_maths_3e_dnb')

    def test_source_downloads_accept_only_official_https_domains(self):
        helper = load_helper()
        for source in helper.SOURCES:
            helper.validate_source_url(source.url)
        for url in ('http://eduscol.education.gouv.fr/a.pdf',
                    'https://eduscol.education.gouv.fr.evil.invalid/a.pdf',
                    'https://user:password@eduscol.education.gouv.fr/a.pdf'):
            with self.assertRaises(ValueError):
                helper.validate_source_url(url)

    def test_rejects_wrong_collection_and_empty_ingestion_responses(self):
        helper = load_helper()
        helper.validate_ingestion_result({'collection': 'rag_maths_premiere', 'added': 2,
                                          'skipped': 0}, 'rag_maths_premiere')
        helper.validate_ingestion_result({'collection': 'rag_maths_premiere', 'added': 0,
                                          'skipped': 2}, 'rag_maths_premiere')
        for result in ({'collection': 'nsi_corpus', 'added': 2, 'skipped': 0},
                       {'status': 'ok', 'message': 'Aucun document chargé.'},
                       {'collection': 'rag_maths_premiere', 'added': 0, 'skipped': 0}):
            with self.assertRaises(ValueError):
                helper.validate_ingestion_result(result, 'rag_maths_premiere')

    def test_api_token_cannot_be_sent_to_an_external_endpoint(self):
        helper = load_helper()
        helper.validate_api_url('http://127.0.0.1:18001')
        helper.validate_api_url('http://korrigo-rag:8001')
        with self.assertRaises(ValueError):
            helper.validate_api_url('https://example.com')


if __name__ == '__main__':
    unittest.main()
