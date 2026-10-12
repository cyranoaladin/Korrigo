#!/usr/bin/env python3
"""Add official maths references to Korrigo's two existing RAG collections.

Default: print a plan, without network calls or filesystem writes.
--prepare: download official PDFs and extract text; no RAG writes.
--apply: prepare, then add through the legacy ingestor's deduplicating API.

Run on the RAG host with --prepare-dir below its existing uploads bind mount.
The default container path is /data/uploads/korrigo-maths-bootstrap-v1.
Supply the existing ingestion credential only through RAG_BOOTSTRAP_TOKEN.
No collection is deleted or replaced. No LLM text generation is performed.
Sources describe the 2025-2026 examinations already stored by Korrigo;
the 2020 programme remains applicable to troisième until rentrée 2028.
"""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from urllib.parse import urlsplit
import urllib.request


ALLOWED_COLLECTIONS = frozenset({'rag_maths_3e_dnb', 'rag_maths_premiere'})
MAX_SOURCE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Source:
    id: str
    collection: str
    url: str
    title: str
    niveau: str
    teaching: str
    programme_version: str
    applicable_period: str
    first_page: int = 1
    last_page: int | None = None


SOURCES = (
    Source(
        'cycle4-2020-maths', 'rag_maths_3e_dnb',
        'https://cache.media.education.gouv.fr/file/31/89/1/ensel714_annexe3_1312891.pdf',
        'Programme de mathématiques du cycle 4 — BO du 30 juillet 2020, pages 126–138',
        '3e', 'Tronc commun', 'BO-2020-07-30', '3e: rentrées 2020 à 2027', 126, 138,
    ),
    Source(
        'attendus-maths-3e', 'rag_maths_3e_dnb',
        'https://eduscol.education.gouv.fr/sites/default/files/document/18-maths-3e-attendus-eduscol1114748pdf-74688.pdf',
        'Attendus de fin d’année de troisième en mathématiques — éduscol, annexe 18',
        '3e', 'Tronc commun', 'Eduscol-2019', '3e: valable en 2025-2026 et 2026-2027',
    ),
    Source(
        'premiere-specialite-2019', 'rag_maths_premiere',
        'https://eduscol.education.gouv.fr/sites/default/files/document/spe632annexe1063168pdf-84156.pdf',
        'Programme de spécialité mathématiques de première générale — BO du 22 janvier 2019',
        'Première', 'Enseignements de spécialité (EDS)', 'BO-2019-01-22',
        'rentrées 2019 à 2025; examens de première 2025-2026',
    ),
    Source(
        'premiere-maths-integrees-2022', 'rag_maths_premiere',
        'https://eduscol.education.gouv.fr/sites/default/files/document/mathematiques-integrees-enssci-1reg-mene2218178a-1pdf-95001.pdf',
        'Mathématiques intégrées à l’enseignement scientifique en première — BO du 7 juillet 2022',
        'Première', 'Tronc commun sans spécialité mathématiques', 'BO-2022-07-07',
        'rentrées 2022 à 2025; examens de première 2025-2026',
    ),
)


def validate_source_url(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or not (host == 'education.gouv.fr' or host.endswith('.education.gouv.fr'))):
        raise ValueError('Source must be an official Ministry HTTPS URL')


def validate_api_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname not in
            {'127.0.0.1', 'localhost', 'korrigo-rag', 'korrigo-maths-rag'}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {'', '/'}):
        raise ValueError('RAG API must be a loopback or dedicated internal endpoint')


def make_payload(source, container_path, source_sha256):
    if source.collection not in ALLOWED_COLLECTIONS:
        raise ValueError('Unapproved collection target')
    validate_source_url(source.url)
    return {
        'source_type': 'markdown',
        'source': container_path,
        # /ingest resolves the target from metadata_hints; top-level is ignored.
        'hints': {
            'collection': source.collection,
            'matiere': 'Mathématiques',
            'domain': 'mathematiques',
            'niveau': source.niveau,
            'groupe': source.teaching,
            'type_ressource': 'Programme officiel ou attendus ministériels',
            'source': source.url,
            'source_uri': source.url,
            'source_label': source.title,
            'drive_file_name': source.title,
            'publisher': 'Ministère de l’Éducation nationale / DGESCO',
            'source_sha256': source_sha256,
            'programme_version': source.programme_version,
            'applicable_period': source.applicable_period,
            'source_pages': f'{source.first_page}–{source.last_page or "fin"}',
            'bootstrap_id': 'korrigo-maths-official-v1',
        },
    }


def prepare_sources(directory, container_directory):
    directory.mkdir(parents=True, exist_ok=True)
    prepared = []
    for source in SOURCES:
        validate_source_url(source.url)
        request = urllib.request.Request(source.url, headers={'User-Agent': 'Korrigo-official-maths-bootstrap/1.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            validate_source_url(response.url)
            pdf = response.read(MAX_SOURCE_BYTES + 1)
        if len(pdf) > MAX_SOURCE_BYTES or not pdf.startswith(b'%PDF-'):
            raise ValueError(f'{source.id}: source is not a bounded PDF')
        pdf_path = directory / f'{source.id}.pdf'
        pdf_path.write_bytes(pdf)
        text_path = directory / f'{source.id}.txt'
        command = ['pdftotext', '-enc', 'UTF-8', '-f', str(source.first_page)]
        if source.last_page is not None:
            command += ['-l', str(source.last_page)]
        command += [str(pdf_path), str(text_path)]
        subprocess.run(command, check=True, capture_output=True)
        text = text_path.read_text(encoding='utf-8').replace('\f', '\n\n').strip()
        if len(text) < 1000:
            raise ValueError(f'{source.id}: extracted text is unexpectedly short')
        # An unchanged official text, with a provenance header, is indexed.
        markdown = f'# {source.title}\n\nSource officielle : {source.url}\n\n{text}\n'
        markdown_path = directory / f'{source.id}.md'
        markdown_path.write_text(markdown, encoding='utf-8')
        source_sha256 = hashlib.sha256(pdf).hexdigest()
        container_path = str(PurePosixPath(container_directory) / markdown_path.name)
        prepared.append({
            'id': source.id,
            'collection': source.collection,
            'pdf_sha256': source_sha256,
            'text_sha256': hashlib.sha256(markdown.encode()).hexdigest(),
            'text_characters': len(text),
            'payload': make_payload(source, container_path, source_sha256),
        })
    (directory / 'manifest.json').write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return prepared


def validate_ingestion_result(result, expected_collection):
    if result.get('collection') != expected_collection:
        raise ValueError('Ingestor did not confirm the requested collection')
    added, skipped = result.get('added'), result.get('skipped')
    if (type(added) is not int or type(skipped) is not int
            or added < 0 or skipped < 0 or added + skipped == 0):
        raise ValueError('Ingestor returned no indexed or previously indexed chunks')


def apply_sources(prepared, api_url, token):
    validate_api_url(api_url)
    if not token:
        raise ValueError('RAG_BOOTSTRAP_TOKEN must be configured for apply')
    results = []
    for item in prepared:
        if item['collection'] not in ALLOWED_COLLECTIONS:
            raise ValueError('Unapproved collection target')
        payload = item['payload']
        if payload.get('hints', {}).get('collection') != item['collection']:
            raise ValueError('Payload collection does not match approved target')
        request = urllib.request.Request(
            api_url.rstrip('/') + '/ingest',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
            method='POST',
        )
        # Do not follow redirects with the ingestion credential.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        with urllib.request.build_opener(NoRedirect).open(request, timeout=300) as response:
            result = json.load(response)
        validate_ingestion_result(result, item['collection'])
        results.append({'id': item['id'], 'collection': result['collection'],
                        'added': result['added'], 'skipped': result['skipped']})
        print(json.dumps({'ingested': results[-1]}, ensure_ascii=False), flush=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--apply', action='store_true')
    parser.add_argument('--prepare-dir', type=Path)
    parser.add_argument('--container-dir', default='/data/uploads/korrigo-maths-bootstrap-v1')
    parser.add_argument('--api-url', default='http://127.0.0.1:18001')
    args = parser.parse_args(argv)
    plan = {'mode': 'apply' if args.apply else 'prepare' if args.prepare else 'plan',
            'collections': sorted(ALLOWED_COLLECTIONS), 'sources': [asdict(s) for s in SOURCES]}
    if not (args.prepare or args.apply):
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.prepare_dir:
        parser.error('--prepare-dir is required for prepare/apply')
    validate_api_url(args.api_url)
    token = os.environ.get('RAG_BOOTSTRAP_TOKEN', '')
    if args.apply and not token:
        raise ValueError('RAG_BOOTSTRAP_TOKEN must be configured for apply')
    prepared = prepare_sources(args.prepare_dir, args.container_dir)
    print(json.dumps({'mode': plan['mode'], 'prepared': [
        {k: v for k, v in item.items() if k != 'payload'} for item in prepared
    ]}, ensure_ascii=False), flush=True)
    if args.apply:
        apply_sources(prepared, args.api_url, token)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        # URLs, tokens, API response bodies and document content stay out of logs.
        print(json.dumps({'error_type': type(exc).__name__, 'operation_failed': True}), file=sys.stderr)
        sys.exit(1)
