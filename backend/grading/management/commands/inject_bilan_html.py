"""
Management command to inject a static bilan HTML file into the Redis cache
so it is served by the existing questionnaire bilan API.

Usage (inside Docker container):
    python manage.py inject_bilan_html /path/to/bilan.html

Usage (from host, via docker exec):
    docker exec -i <backend_container> python manage.py inject_bilan_html /app/bilan.html
"""
import re

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from grading.questionnaire_bilan import (
    QUESTIONNAIRE_BILAN_CACHE_KEY,
    _compute_fingerprint,
    build_questionnaire_summary,
    serialize_questionnaire_responses,
)


class Command(BaseCommand):
    help = 'Inject a static bilan HTML file into the questionnaire bilan Redis cache'

    def add_arguments(self, parser):
        parser.add_argument('html_file', type=str, help='Path to the bilan HTML file')

    def handle(self, *args, **options):
        html_file = options['html_file']

        # Read the HTML file
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {html_file}'))
            return

        # Extract <style> block
        style_match = re.search(r'(<style[^>]*>.*?</style>)', html_content, re.DOTALL)
        style_block = style_match.group(1) if style_match else ''

        # Extract body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
        if body_match:
            body_content = body_match.group(1).strip()
        else:
            body_content = html_content

        # Scope CSS to avoid conflicts with existing page styles
        # Wrap everything in a scoped div
        scoped_css = style_block
        # Replace generic selectors to scope them
        scoped_css = scoped_css.replace('body {', '.bilan-injected-content {')
        scoped_css = scoped_css.replace('body{', '.bilan-injected-content{')

        # Combine: scoped style + wrapped body
        final_html = f'{scoped_css}\n<div class="bilan-injected-content">\n{body_content}\n</div>'

        # Compute fingerprint from current questionnaire data
        serialized = serialize_questionnaire_responses()
        summary = build_questionnaire_summary()
        fingerprint = _compute_fingerprint(serialized, summary)

        # Build cache entry matching the expected format
        cache_entry = {
            'status': 'ready',
            'html': final_html,
            'generated_at': timezone.now().isoformat(),
            'detail': '',
            'auto': True,
            'fingerprint': fingerprint,
            'responses_count': summary['responses_count'],
            'total_eligible': summary['total_eligible'],
            'model': 'static-bilan-html',
        }

        # Store in Redis cache (no timeout = permanent)
        cache.set(QUESTIONNAIRE_BILAN_CACHE_KEY, cache_entry, timeout=None)

        self.stdout.write(self.style.SUCCESS(
            f'Bilan HTML injected successfully!\n'
            f'  - Source: {html_file}\n'
            f'  - HTML size: {len(final_html)} chars\n'
            f'  - Fingerprint: {fingerprint[:16]}...\n'
            f'  - Cache key: {QUESTIONNAIRE_BILAN_CACHE_KEY}\n'
            f'  - Responses: {summary["responses_count"]}/{summary["total_eligible"]}'
        ))
