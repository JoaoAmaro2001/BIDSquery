# utils/merge_participant_excels.py
"""
Merge one or more participant Excel files into a single, app-ready file.

- Requires exactly two mandatory columns in the output:
    * name
    * participant_id           (always normalized to start with 'sub-')
- Tries to 'uniformize' common header variants (e.g., 'Participant', 'ID',
  'Participant ID', 'Subject', 'sub_id' -> 'participant_id'; 'Full Name',
  'participant_name' -> 'name', etc.)
- Preserves ALL other columns from every input (column union). For rows/files
  that don't have a given optional column, the cell is left blank.
- Writes a single-sheet Excel with mandatory columns first, then optionals.

CLI:
    python -m utils.merge_participant_excels input1.xlsx input2.xlsx ... -o merged_participants.xlsx
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


# --- Common header aliases to canonical names ---
# Keys are canonical column names, values are lists of likely variants.
ALIASES: Dict[str, List[str]] = {
    "participant_id": [
        "participant_id", "participant id", "participant", "id", "subject",
        "subject_id", "subject id", "sub", "sub_id", "sub id", "pid",
        "codigo_participante", "código participante", "id_participante",
    ],
    "name": [
        "name", "participant_name", "participant name", "fullname", "full name",
        "nome", "nome completo",
    ],
    # You can extend with common optional fields to lightly unify them too:
    "age": ["age", "idade", "age_years"],
    "gender": ["gender", "sexo", "sex", "género", "genero"],
    "email": ["email", "e-mail", "mail"],
    "phone": ["phone", "telefone", "tel", "mobile", "telemovel", "telemóvel"],
    "group": ["group", "grupo", "condition", "condição", "arm"],
    "site": ["site", "centro", "center", "centre", "location"],
    "session": ["session", "sessao", "sessão", "visit", "wave"],
    "notes": ["notes", "observacoes", "observações", "remarks", "comment"],
}

MANDATORY = ["name", "participant_id"]


def _clean_header(h: str) -> str:
    """Normalize a header string: lowercase, trim, collapse spaces, remove punctuation to underscores."""
    h = (h or "").strip().lower()
    h = re.sub(r"\s+", " ", h)
    # Replace separators with spaces first, then underscore
    h = h.replace("-", " ").replace("/", " ").replace("\\", " ")
    h = re.sub(r"[^a-z0-9 ]+", "", h)
    h = h.strip().replace("  ", " ")
    return h


def _alias_to_canonical(col: str) -> str:
    """Map a cleaned header to a canonical name if it matches a known alias."""
    cleaned = _clean_header(col)
    for canonical, variants in ALIASES.items():
        if cleaned in { _clean_header(v) for v in variants }:
            return canonical
    return cleaned  # keep as-is if not in aliases


def _normalize_participant_id(value) -> str:
    """
    Ensure participant_id is a string that starts with 'sub-'.
    Examples:
        01          -> sub-01
        '1'         -> sub-1
        'sub-01'    -> sub-01 (unchanged)
        'sub_02'    -> sub-02
        'SUB 03'    -> sub-03
        'subject-4' -> sub-4
    """
    if pd.isna(value):
        return ""
    s = str(value).strip()
    # Remove any leading 'sub', 'subject', separators, then re-attach 'sub-'
    s = re.sub(r"^(subject|sub)[\s_\-]*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    return f"sub-{s}" if s else ""


def _standardize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with headers normalized and canonicalized via ALIASES."""
    df = df.copy()
    rename_map = { c: _alias_to_canonical(c) for c in df.columns }
    # Resolve collisions (e.g., two different columns mapping to the same canonical)
    # by letting the first occurrence win and appending suffix to later duplicates.
    seen = {}
    final_map = {}
    for original, canonical in rename_map.items():
        if canonical not in seen:
            seen[canonical] = 1
            final_map[original] = canonical
        else:
            seen[canonical] += 1
            final_map[original] = f"{canonical}__{seen[canonical]}"
    return df.rename(columns=final_map)


def _ensure_mandatory(df: pd.DataFrame, src_name: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Make sure 'name' and 'participant_id' exist.
    If not present, try to synthesize (only 'participant_id' is truly critical).
    Returns (df, missing) with list of still-missing mandatory columns.
    """
    df = df.copy()

    # If we have something that looks like a name but under an alias, _standardize_headers already handled it.
    # Now just check presence.
    missing = [c for c in MANDATORY if c not in df.columns]

    # If participant_id missing but there is any column that looks like an ID variant we didn't catch,
    # try to guess the best candidate (fallback heuristic).
    if "participant_id" in missing:
        # Heuristic: prefer a single column whose name contains 'id' or 'subject' or 'sub'
        candidates = [c for c in df.columns if re.search(r"\b(id|subject|sub)\b", c)]
        if candidates:
            chosen = candidates[0]
            df["participant_id"] = df[chosen]
            if "participant_id" in missing:
                missing.remove("participant_id")

    # If name is missing, try common fallbacks
    if "name" in missing:
        for candidate in ["fullname", "full_name", "participant_name"]:
            if candidate in df.columns:
                df["name"] = df[candidate]
                missing.remove("name")
                break
        if "name" in missing:
            # Create empty if still missing
            df["name"] = ""

    return df, [m for m in MANDATORY if m not in df.columns]


def load_excel_any_sheet(path: Path) -> pd.DataFrame:
    """
    Load an Excel file; if multiple sheets, prefer the first non-empty.
    """
    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        if not df.empty:
            return df
    # If all empty, return empty DF
    return pd.DataFrame()


def merge_participant_excels(
    input_paths: Iterable[Path],
    output_path: Path,
    sheet_name: str = "participants",
) -> pd.DataFrame:
    """
    Merge multiple participant Excel files into one canonical Excel for the app.
    Returns the merged DataFrame and writes it to `output_path`.
    """
    input_paths = [Path(p) for p in input_paths]
    frames: List[pd.DataFrame] = []
    problems: List[str] = []

    for p in input_paths:
        try:
            df = load_excel_any_sheet(p)
            if df.empty:
                problems.append(f"{p.name}: empty or no parsable sheets")
                continue

            df = _standardize_headers(df)
            df, missing = _ensure_mandatory(df, p.name)

            # Enforce mandatory columns presence (participant_id is critical)
            if "participant_id" in missing:
                problems.append(f"{p.name}: could not find/derive 'participant_id'")
                continue

            # Normalize columns types for mandatory fields
            if "name" in df.columns:
                df["name"] = df["name"].astype(str).fillna("").str.strip()

            df["participant_id"] = df["participant_id"].apply(_normalize_participant_id)

            # Ensure mandatory columns are first in this frame (for readability)
            other_cols = [c for c in df.columns if c not in MANDATORY]
            df = df[MANDATORY + other_cols]

            # Keep a source marker (optional, can help trace provenance)
            if "source_file" not in df.columns:
                df["source_file"] = p.name

            frames.append(df)

        except Exception as e:
            problems.append(f"{p.name}: {e}")

    if not frames:
        raise RuntimeError(
            "No valid participant rows found in the supplied files.\n" +
            ("\n".join(problems) if problems else "")
        )

    # Column union across all frames
    all_cols: List[str] = []
    for f in frames:
        for c in f.columns:
            if c not in all_cols:
                all_cols.append(c)

    # Reindex each frame to the union, fill missing with blank
    frames = [f.reindex(columns=all_cols) for f in frames]
    merged = pd.concat(frames, ignore_index=True)

    # Remove exact duplicate rows (keep first)
    merged = merged.drop_duplicates()

    # Sort columns: mandatory first, then the rest alphabetically (but keep source_file last)
    optionals = [c for c in merged.columns if c not in MANDATORY and c != "source_file"]
    optionals_sorted = sorted(optionals)
    final_cols = MANDATORY + optionals_sorted + (["source_file"] if "source_file" in merged.columns else [])
    merged = merged.reindex(columns=final_cols)

    # Basic sanity check: participant_id must start with 'sub-'
    if not merged["participant_id"].fillna("").map(lambda x: str(x).startswith("sub-")).all():
        raise AssertionError("Internal error: some participant_id values do not start with 'sub-' after normalization.")

    # Write Excel
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        merged.to_excel(writer, index=False, sheet_name=sheet_name)

    # If there were non-fatal problems, print them (could also log)
    if problems:
        print("Completed with warnings:")
        for msg in problems:
            print("  -", msg)

    return merged


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Merge participant Excel files into a single app-ready table.")
    ap.add_argument("inputs", nargs="+", help="One or more Excel files (.xlsx, .xls).")
    ap.add_argument("-o", "--output", required=True, help="Path to the output Excel file.")
    ap.add_argument("-s", "--sheet", default="participants", help="Name of the output sheet (default: participants).")
    return ap.parse_args(argv)


def main():
    args = _parse_args()
    in_paths = [Path(p) for p in args.inputs]
    out_path = Path(args.output)
    merge_participant_excels(in_paths, out_path, sheet_name=args.sheet)
    print(f"✅ Merged {len(in_paths)} file(s) → {out_path}")


if __name__ == "__main__":
    main()
