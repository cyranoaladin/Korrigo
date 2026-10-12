import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get('KORRIGO_PROXY_HTTP_TEST') == '1', 'Opt-in Docker HTTP integration')
class InferenceProxyHTTPTests(unittest.TestCase):
    def test_credentials_are_case_sensitive_and_mutation_routes_are_closed(self):
        spec = importlib.util.spec_from_file_location('proxy_renderer', ROOT/'scripts/ops/render_inference_proxy.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'nginx.conf'
            config.write_text(module.render_proxy((ROOT/'infra/nginx/inference-proxy.conf.template').read_text(),
                              'client-test-token-1234567890', 'upstream-test-token-1234567890'))
            cid = subprocess.check_output(['docker','run','-d','--rm','--entrypoint','nginx',
                  '-p','127.0.0.1::8001','-v',f'{config}:/etc/nginx/nginx.conf:ro',
                  'nginx:1.30.5-alpine','-g','daemon off;'], text=True).strip()
            try:
                info = json.loads(subprocess.check_output(['docker','inspect',cid]))[0]
                port = info['NetworkSettings']['Ports']['8001/tcp'][0]['HostPort']
                url = f'http://127.0.0.1:{port}'
                for attempt in range(20):
                    try:
                        urllib.request.urlopen(url+'/health',timeout=2).close()
                        break
                    except OSError:
                        if attempt == 19: raise
                        time.sleep(.1)
                def status(path, token, method='POST'):
                    request = urllib.request.Request(url+path, method=method,
                              headers={'Authorization':'Bearer '+token})
                    try:
                        with urllib.request.urlopen(request,timeout=2) as response: return response.status
                    except urllib.error.HTTPError as error: return error.code
                self.assertEqual(status('/search','CLIENT-TEST-TOKEN-1234567890'),401)
                self.assertEqual(status('/search','wrong-test-token-1234567890'),401)
                self.assertEqual(status('/search','client-test-token-1234567890','GET'),403)
                self.assertEqual(status('/ingest','client-test-token-1234567890'),404)
            finally:
                subprocess.run(['docker','rm','-f',cid],capture_output=True,check=True)


if __name__ == '__main__':
    unittest.main()
