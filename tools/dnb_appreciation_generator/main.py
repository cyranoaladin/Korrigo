"""
Point d'entrée du générateur d'appréciations Korrigo.
Analyse chirurgicale des copies : Scores par exercice + Barème + Annotations.
Propulsé par Kimi K2.6 (Mode Thinking).
"""

import argparse
import csv
import math
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

from config import Config
from fallback import generate as fallback_generate
from llm_client import LLMError, generate as llm_generate
from prompt_builder import SYSTEM_PROMPT, build_correction_prompt, build_user_prompt
from validator import validate

# Configuration du logging professionnel
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lecture et parsing enrichi
# ---------------------------------------------------------------------------

def read_input_csv(path: Path, strict: bool) -> List[Dict[str, Any]]:
    """
    Lit le CSV d'entrée. 
    Gère les scores (float) et les métadonnées textuelles (remarques/annotations).
    """
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Le fichier {path} est introuvable.")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for raw in reader:
            parsed: Dict[str, Any] = {}
            for key, val in raw.items():
                k = key.strip().lower()
                v = val.strip()
                
                # Gestion des colonnes textuelles (Logique Métier Korrigo)
                if k in ["student_id", "remarks", "annotations", "student_name"]:
                    parsed[k] = v
                # Gestion des colonnes numériques (Scores)
                else:
                    if v == "":
                        if strict:
                            raise ValueError(f"Valeur manquante pour {key} (ID: {raw.get('student_id')})")
                        parsed[k] = 0.0
                    else:
                        try:
                            parsed[k] = float(v.replace(",", "."))
                        except ValueError:
                            parsed[k] = 0.0 # Fallback sécurisé
            rows.append(parsed)
    return rows

# ---------------------------------------------------------------------------
# Logique Pédagogique : Analyse de l'Écart (Diagnostic)
# ---------------------------------------------------------------------------

def perform_pedagogical_diagnostic(row: Dict[str, Any], cfg: Config) -> Dict[str, Any]:
    """
    Analyse l'écart entre le barème et les points obtenus.
    Identifie les points forts et les lacunes critiques.
    """
    # Définition du barème théorique (à adapter selon votre sujet)
    bareme = {
        "partie1": 6.0,
        "e2_total": 3.0,
        "e3_total": 3.5,
        "e4_total": 3.0,
        "e5_total": 4.5
    }
    
    total, p1, e2, e3, e4, e5 = compute_totals(row)
    
    # Calcul des ratios de réussite par bloc
    diagnostics = {
        "total": total,
        "strengths": [],
        "weaknesses": [],
        "annotations": row.get("annotations", ""),
        "remarks": row.get("remarks", "")
    }

    scores = {"Partie 1": p1, "Ex 2": e2, "Ex 3": e3, "Ex 4": e4, "Ex 5": e5}
    
    for label, score in scores.items():
        key = label.lower().replace(" ", "") if "Partie" in label else f"e{label[-1]}_total"
        max_p = bareme.get(key, 1.0)
        ratio = score / max_p
        
        if ratio >= cfg.success_threshold:
            diagnostics["strengths"].append(label)
        elif ratio <= cfg.failure_threshold:
            diagnostics["weaknesses"].append(label)
            
    return diagnostics

def compute_totals(row: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    """Agrège les points par bloc."""
    p1 = row.get("partie1", 0.0)
    e2 = sum(row.get(f"e2_q{i}", 0.0) for i in range(1, 6))
    e3 = sum(row.get(f"e3_q{i}", 0.0) for i in range(1, 6))
    e4 = sum(row.get(f"e4_q{i}", 0.0) for i in range(1, 5))
    e5 = (sum(row.get(f"e5_q{i}", 0.0) for i in range(1, 4)) + 
          row.get("e5_q4a", 0.0) + row.get("e5_q4b", 0.0) + 
          row.get("e5_q4c", 0.0) + row.get("e5_q4d", 0.0))
    
    total = p1 + e2 + e3 + e4 + e5
    return total, p1, e2, e3, e4, e5

# ---------------------------------------------------------------------------
# Orchestration de la Génération
# ---------------------------------------------------------------------------

def generate_appreciation(row: Dict[str, Any], cfg: Config, fallback_only: bool = False) -> Dict[str, str]:
    """Gère le cycle de vie de la génération via Kimi K2.6."""
    
    diag = perform_pedagogical_diagnostic(row, cfg)
    
    result = {
        "raw_text": "",
        "appreciation": "",
        "source": "llm",
        "attempts": "0",
        "rejection_reason": "",
    }

    if fallback_only:
        result["appreciation"] = "Analyse indisponible." 
        result["source"] = "none"
        return result

    # Construction du prompt sémantique (Utilise diag['strengths'], diag['weaknesses'], diag['annotations'])
    user_prompt = build_user_prompt(diag, cfg)

    for attempt in range(1, cfg.max_llm_retries + 1):
        try:
            # Appel au mode Thinking de Kimi
            raw = llm_generate(cfg.system_instruction, user_prompt, cfg)
            
            # Validation pédagogique (longueur, mots interdits)
            is_valid, reason = validate(raw, cfg)
            if is_valid:
                result["appreciation"] = raw
                result["attempts"] = str(attempt)
                return result
            else:
                result["rejection_reason"] = reason
                # On ajuste le prompt pour la tentative suivante
                user_prompt = build_correction_prompt(raw, reason)
                
        except LLMError as exc:
            logger.error(f"Erreur Kimi : {exc}")
            continue

    # Si échec -> Fallback déterministe basé sur les labels de qualité
    result["appreciation"] = fallback_generate(diag, cfg)
    result["source"] = "fallback"
    return result

# ---------------------------------------------------------------------------
# Entrée principale (CLI)
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Korrigo - Générateur de Rétroaction IA")
    parser.add_argument("--input", "-i", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = Config() # Charge la config Kimi K2.6 par défaut
    
    try:
        rows = read_input_csv(args.input, strict=False)
    except Exception as e:
        logger.error(f"Erreur lecture CSV : {e}")
        return 1

    final_results = []
    logger.info(f"Démarrage de l'analyse pour {len(rows)} copies...")

    for row in rows:
        res = generate_appreciation(row, cfg)
        # Fusion des données pour le CSV final
        total, _, _, _, _, _ = compute_totals(row)
        out_row = {
            "student_id": row.get("student_id"),
            "total_score": round(total, 2),
            "appreciation": res["appreciation"],
            "source": res["source"],
            "remarks_original": row.get("remarks", ""),
            "attempts": res["attempts"]
        }
        final_results.append(out_row)
        
        if args.dry_run:
            print(f"--- ID: {out_row['student_id']} ({out_row['total_score']}/20) ---")
            print(f"Appréciation : {out_row['appreciation']}\n")

    if not args.dry_run:
        with args.output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=final_results[0].keys())
            writer.writeheader()
            writer.writerows(final_results)
        logger.info(f"Succès : Fichier généré -> {args.output}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
