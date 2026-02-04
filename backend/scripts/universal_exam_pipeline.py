#!/usr/bin/env python3
"""
Pipeline Universel d'Indexation et de Reconstruction A3 → A4
PRD-19: Moteur industriel de traitement de copies d'examen
"""
import os, sys, csv, json, logging, argparse, unicodedata, re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import fitz, cv2, numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ROI_300DPI = {'x': 3720, 'y': 50, 'width': 1100, 'height': 650}
THRESHOLD_NAME = 0.80
THRESHOLD_DOB_PIVOT = 0.50

@dataclass
class StudentRecord:
    id: int; raw_name: str; last_name: str; first_name: str
    last_name_norm: str; first_name_norm: str; full_name_norm: str
    dob: str; dob_norm: str; classe: str = ""

@dataclass
class CopySegment:
    student: Optional[StudentRecord]; start_a3: int; end_a3: int
    leaf_count: int; score: float; ocr_name: str; ocr_date: str
    status: str; needs_rotation: bool = False

@dataclass
class ProcessingResult:
    student_name: str; student_id: int; output_file: str
    page_count: int; leaf_count: int; score: float; status: str; error: str = ""

class UniversalExamPipeline:
    def __init__(self, pdf_path, csv_path, output_dir, api_key=None, model=None, dpi=300):
        self.pdf_path, self.csv_path, self.output_dir = pdf_path, csv_path, output_dir
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14')
        self.dpi = dpi
        self.students, self.segments, self.results = [], [], []
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def load_csv(self):
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(2048); f.seek(0)
            delim = ';' if ';' in sample and ',' not in sample else ','
            for idx, row in enumerate(csv.DictReader(f, delimiter=delim)):
                name = next((row[c].strip() for c in ['Élèves','Eleves','NOM','Nom'] if c in row and row[c].strip()), "")
                if not name: continue
                parts = name.split(' ', 1)
                ln, fn = parts[0], parts[1] if len(parts) > 1 else ""
                dob = next((row[c].strip() for c in ['Né(e) le','DATE_NAISSANCE'] if c in row and row[c].strip()), "")
                cls = next((row[c].strip() for c in ['Classe','CLASSE'] if c in row and row[c].strip()), "")
                self.students.append(StudentRecord(idx+1, name, ln, fn, self._norm(ln), self._norm(fn), 
                    self._norm(f"{ln} {fn}"), dob, re.sub(r'[^\d]','',dob), cls))
        logger.info(f"CSV: {len(self.students)} students")
        return self.students

    def _norm(self, t):
        if not t: return ""
        t = unicodedata.normalize('NFD', t.upper())
        return ' '.join(re.sub(r'[^A-Z\s]', '', ''.join(c for c in t if unicodedata.category(c) != 'Mn')).split())

    def _extract_roi(self, page):
        mat = fitz.Matrix(self.dpi/72, self.dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR if pix.n==3 else cv2.COLOR_RGBA2BGR)
        h, w = img.shape[:2]
        right = img[:, w//2:]  # Partie droite de la page A3
        rh, rw = right.shape[:2]
        # ROI: toute la largeur, 25% hauteur (header complet)
        roi = right[:int(rh*0.25), :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

    def _ocr(self, img):
        import base64, openai
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        b64 = base64.b64encode(buf).decode()
        try:
            client = openai.OpenAI(api_key=self.api_key)
            r = client.chat.completions.create(model=self.model, max_tokens=200, temperature=0.1,
                messages=[{"role":"user","content":[{"type":"text","text":'Extract: {"NOM":"...","PRENOM":"...","DATE_NAISSANCE":"DD/MM/YYYY"}'},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}","detail":"high"}}]}])
            m = re.search(r'\{[^}]+\}', r.choices[0].message.content)
            if m:
                d = json.loads(m.group())
                return {'last_name': d.get('NOM','').upper(), 'first_name': d.get('PRENOM','').upper(), 'dob': d.get('DATE_NAISSANCE','')}
        except Exception as e: logger.error(f"OCR: {e}")
        return {'last_name':'', 'first_name':'', 'dob':''}

    def _match(self, ocr):
        if not ocr['last_name'] and not ocr['first_name']: return None, 0, {}
        ol, of, od = self._norm(ocr['last_name']), self._norm(ocr['first_name']), re.sub(r'[^\d]','',ocr['dob'])
        best, bscore, bval = None, 0, {}
        for s in self.students:
            ls = SequenceMatcher(None, ol, s.last_name_norm).ratio()
            fs = SequenceMatcher(None, of, s.first_name_norm).ratio()
            ns = ls*0.6 + fs*0.4
            dm = od == s.dob_norm if od and s.dob_norm else False
            valid = (ns >= THRESHOLD_NAME and dm) or (ns >= THRESHOLD_DOB_PIVOT and dm)
            score = ns + (0.2 if dm else 0)
            if score > bscore: best, bscore, bval = s, score, {'valid': valid, 'name': ns, 'dob': dm}
        return best, bscore, bval

    def identify_segments(self):
        doc = fitz.open(self.pdf_path)
        cur = None
        for i in range(doc.page_count):
            if i % 2 == 0:
                roi = self._extract_roi(doc.load_page(i))
                ocr = self._ocr(roi)
                st, sc, val = self._match(ocr)
                status = 'VALIDATED' if val.get('valid') else ('AMBIGUOUS' if sc >= 0.6 else 'NO_MATCH')
                if cur and st and cur.student and st.id == cur.student.id:
                    cur.end_a3, cur.leaf_count = i+1, cur.leaf_count+1; continue
                if cur: self.segments.append(cur)
                cur = CopySegment(st, i, i+1, 1, sc, f"{ocr['last_name']} {ocr['first_name']}", ocr['dob'], status)
                logger.info(f"P{i+1}: {cur.ocr_name} -> {st.raw_name if st else 'NO'} [{status}]")
        if cur: self.segments.append(cur)
        doc.close()
        return self.segments

    def generate_pdfs(self):
        doc = fitz.open(self.pdf_path)
        for seg in self.segments:
            if not seg.student: self.results.append(ProcessingResult(seg.ocr_name,0,"",0,seg.leaf_count,seg.score,"SKIP")); continue
            s = seg.student
            fname = f"{re.sub(r'[^A-Za-z0-9_-]','_',s.raw_name)}_{s.classe or 'X'}.pdf"
            out = fitz.open()
            pages, ln = [], 0
            for a3 in range(seg.start_a3, seg.end_a3+1):
                if a3 >= doc.page_count: break
                p, odd = doc.load_page(a3), a3%2==0
                if odd: ln += 1
                rp = 1+4*(ln-1) if odd else 3+4*(ln-1)
                lp = 4+4*(ln-1) if odd else 2+4*(ln-1)
                r = p.rect; mx = r.width/2
                pages.extend([(lp, p, fitz.Rect(0,0,mx,r.height)), (rp, p, fitz.Rect(mx,0,r.width,r.height))])
            pages.sort(key=lambda x: x[0])
            for _, sp, cr in pages:
                np_ = out.new_page(width=595, height=842)
                np_.show_pdf_page(fitz.Rect(0,0,595,842), doc, sp.number, clip=cr)
            path = os.path.join(self.output_dir, fname)
            out.save(path); out.close()
            self.results.append(ProcessingResult(s.raw_name, s.id, path, len(pages), seg.leaf_count, seg.score, "OK"))
            logger.info(f"Gen: {fname} ({len(pages)}p)")
        doc.close()
        return self.results

    def generate_report(self):
        rpt = {"generated": datetime.now().isoformat(), "pdf": self.pdf_path, "csv": self.csv_path,
            "summary": {"total": len(self.results), "ok": sum(1 for r in self.results if r.status=="OK")},
            "copies": [asdict(r) for r in self.results]}
        path = os.path.join(self.output_dir, "rapport_final.json")
        with open(path, 'w', encoding='utf-8') as f: json.dump(rpt, f, indent=2, ensure_ascii=False)
        logger.info(f"Report: {path}")
        return path

    def process(self):
        logger.info("="*50 + "\nUNIVERSAL EXAM PIPELINE\n" + "="*50)
        self.load_csv()
        self.identify_segments()
        self.generate_pdfs()
        return self.generate_report()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pdf', required=True); p.add_argument('--csv', required=True)
    p.add_argument('--output', required=True); p.add_argument('--dpi', type=int, default=300)
    a = p.parse_args()
    try: from dotenv import load_dotenv; load_dotenv()
    except: pass
    UniversalExamPipeline(a.pdf, a.csv, a.output, dpi=a.dpi).process()

if __name__ == '__main__': main()
