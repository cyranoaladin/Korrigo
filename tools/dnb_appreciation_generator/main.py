"""Point d'entrée du générateur d'appréciations DNB.

Usage :
    python main.py --input notes.csv --output resultats.csv
    python main.py --input notes.csv --dry-run
    python main.py --input notes.csv --fallback-only
"""

import argparse
import csv
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from config import Config
from fallback import generate as fallback_generate
from llm_client import LLMError, generate as llm_generate
from prompt_builder import SYSTEM_PROMPT, build_correction_prompt, build_user_prompt
from validator import validate


# ---------------------------------------------------------------------------
# Lecture et parsing
# ---------------------------------------------------------------------------

def read_input_csv(path: Path, strict: bool) -> List[Dict[str, float]]:
    """Lit le CSV d'entrée et retourne une liste de dicts de scores."""
    rows: List[Dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for raw in reader:
            parsed: Dict[str, float] = {}
            for key, val in raw.items():
                key_norm = key.strip().lower()
                if key_norm == "student_id":
                    parsed["student_id"] = val.strip()
                    continue
                val_stripped = val.strip()
                if val_stripped == "":
                    if strict:
                        raise ValueError(f"Valeur manquante pour {key} (student_id={raw.get('student_id')})")
                    parsed[key_norm] = 0.0
                else:
                    try:
                        parsed[key_norm] = float(val_stripped.replace(",", "."))
                    except ValueError as exc:
                        raise ValueError(f"Valeur invalide '{val}' pour {key}") from exc
            rows.append(parsed)
    return rows


# ---------------------------------------------------------------------------
# Calculs métriques
# ---------------------------------------------------------------------------

def compute_level(total: float, cfg: Config) -> str:
    """Détermine le niveau global à partir du total sur 20."""
    for bound, label in cfg.level_thresholds:
        if total <= bound:
            return label
    return cfg.level_thresholds[-1][1]


def compute_regularity(
    partie1: float,
    e2_total: float,
    e3_total: float,
    e4_total: float,
    e5_total: float,
    cfg: Config,
) -> str:
    """Calcule le profil de régularité à partir des 5 blocs normalisés."""
    ratios = [
        partie1 / 6.0,
        e2_total / 3.0,
        e3_total / 3.5,
        e4_total / 3.0,
        e5_total / 4.5,
    ]
    mean = sum(ratios) / len(ratios)
    variance = sum((r - mean) ** 2 for r in ratios) / len(ratios)
    std = math.sqrt(variance)
    r_range = max(ratios) - min(ratios)

    if std <= cfg.regularity_std_low and r_range <= cfg.regularity_range_low:
        return "homogène"
    if std >= cfg.regularity_std_high or r_range >= cfg.regularity_range_high:
        return "très irrégulier"
    return "irrégulier"


def compute_totals(row: Dict[str, float]) -> Tuple[float, float, float, float, float, float]:
    """Agrège les notes détaillées en sous-totaux par bloc et total général."""
    partie1 = row.get("partie1", 0.0)

    e2_total = sum(row.get(f"e2_q{i}", 0.0) for i in range(1, 6))
    e3_total = sum(row.get(f"e3_q{i}", 0.0) for i in range(1, 6))
    e4_total = sum(row.get(f"e4_q{i}", 0.0) for i in range(1, 5))
    e5_total = (
        sum(row.get(f"e5_q{i}", 0.0) for i in range(1, 4))
        + row.get("e5_q4a", 0.0)
        + row.get("e5_q4b", 0.0)
        + row.get("e5_q4c", 0.0)
        + row.get("e5_q4d", 0.0)
    )

    total = partie1 + e2_total + e3_total + e4_total + e5_total
    return total, partie1, e2_total, e3_total, e4_total, e5_total


# ---------------------------------------------------------------------------
# Génération avec retry
# ---------------------------------------------------------------------------

def generate_appreciation(
    total: float,
    partie1: float,
    e2_total: float,
    e3_total: float,
    e4_total: float,
    e5_total: float,
    cfg: Config,
    fallback_only: bool = False,
) -> Dict[str, str]:
    """Orchestre l'appel LLM, la validation, le retry et le fallback."""

    level_label = compute_level(total, cfg)
    regularity = compute_regularity(partie1, e2_total, e3_total, e4_total, e5_total, cfg)

    result = {
        "level": level_label,
        "regularity": regularity,
        "raw_text": "",
        "appreciation": "",
        "source": "",
        "status": "",
        "attempts": "0",
        "rejection_reason": "",
    }

    if fallback_only:
        result["appreciation"] = fallback_generate(level_label, regularity, cfg)
        result["source"] = "fallback"
        result["status"] = "ok_fallback_forced"
        return result

    user_prompt = build_user_prompt(total, partie1, e2_total, e3_total, e4_total, e5_total, level_label, regularity, cfg)

    for attempt in range(1, cfg.max_llm_retries + 1):
        try:
            if attempt == 1:
                raw = llm_generate(SYSTEM_PROMPT, user_prompt, cfg)
            else:
                correction_prompt = build_correction_prompt(result["raw_text"], result["rejection_reason"])
                raw = llm_generate(SYSTEM_PROMPT, correction_prompt, cfg)
        except LLMError as exc:
            result["rejection_reason"] = f"erreur_llm: {exc}"
            result["raw_text"] = ""
            continue

        result["raw_text"] = raw
        is_valid, reason = validate(raw, cfg)
        if is_valid:
            result["appreciation"] = raw
            result["source"] = "llm"
            result["status"] = "ok"
            result["attempts"] = str(attempt)
            result["rejection_reason"] = ""
            return result
        else:
            result["rejection_reason"] = reason

    # Échec après tous les retries -> fallback
    result["appreciation"] = fallback_generate(level_label, regularity, cfg)
    result["source"] = "fallback"
    result["status"] = "ok_fallback"
    result["attempts"] = str(cfg.max_llm_retries)
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def write_output_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    """Écrit le CSV de sortie enrichi."""
    if not rows:
        return
    fieldnames = [
        "student_id",
        "partie1",
        "e2_total",
        "e3_total",
        "e4_total",
        "e5_total",
        "total",
        "level",
        "regularity",
        "appreciation",
        "source",
        "status",
        "attempts",
        "rejection_reason",
        "raw_text",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Générateur d'appréciations DNB")
    parser.add_argument("--input", "-i", type=Path, required=True, help="CSV d'entrée")
    parser.add_argument("--output", "-o", type=Path, required=True, help="CSV de sortie")
    parser.add_argument("--endpoint", default="http://localhost:11434/api/generate", help="Endpoint Ollama")
    parser.add_argument("--model", default="qwen2.5:7b", help="Nom du modèle Ollama")
    parser.add_argument("--temperature", type=float, default=0.2, help="Température LLM")
    parser.add_argument("--mode", choices=["strict", "permissif"], default="strict", help="Mode de gestion des valeurs manquantes")
    parser.add_argument("--retries", type=int, default=2, help="Nombre de retries LLM")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les résultats sans écrire le fichier")
    parser.add_argument("--fallback-only", action="store_true", help="Utilise uniquement le fallback déterministe")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    cfg = Config(
        ollama_endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_llm_retries=args.retries,
    )

    strict_mode = args.mode == "strict"
    raw_rows = read_input_csv(args.input, strict=strict_mode)

    output_rows: List[Dict[str, object]] = []
    for raw in raw_rows:
        student_id = str(raw.get("student_id", ""))
        total, p1, e2, e3, e4, e5 = compute_totals(raw)
        result = generate_appreciation(total, p1, e2, e3, e4, e5, cfg, fallback_only=args.fallback_only)

        out = {
            "student_id": student_id,
            "partie1": round(p1, 2),
            "e2_total": round(e2, 2),
            "e3_total": round(e3, 2),
            "e4_total": round(e4, 2),
            "e5_total": round(e5, 2),
            "total": round(total, 2),
            **result,
        }
        output_rows.append(out)

        if args.dry_run:
            print(f"[{student_id}] {out['total']}/20 | {out['level']} | {out['regularity']} | {out['source']}")
            print(f"  -> {out['appreciation']}")
            if out["status"] != "ok" and out["rejection_reason"]:
                print(f"  ! {out['status']} : {out['rejection_reason']}")

    if not args.dry_run:
        write_output_csv(args.output, output_rows)
        print(f"Résultats écrits dans {args.output}")

    # Résumé
    total_rows = len(output_rows)
    llm_ok = sum(1 for r in output_rows if r["source"] == "llm")
    fallback_ok = sum(1 for r in output_rows if r["source"] == "fallback")
    print(f"\nRésumé : {total_rows} traitées | LLM={llm_ok} | Fallback={fallback_ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
