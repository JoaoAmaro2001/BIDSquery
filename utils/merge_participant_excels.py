# utils/merge_participant_excels.py
from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Sequence
from datetime import datetime, date
import pandas as pd

# ---------- Aliases (header unification) ----------
ALIASES: Dict[str, List[str]] = {
    "participant_id": [
        "participant_id", "participant id", "participant", "id", "subject",
        "subject_id", "subject id", "sub", "sub_id", "sub id", "pid",
        "codigo_participante", "código participante", "id_participante", "id participante",
        "participant code", "code", "subject code", "subject-code", "code number"
    ],
    "name": [
        "name", "participant_name", "participant name", "fullname", "full name",
        "nome", "nome completo", "first name", "first_name", "firstname", "primeiro nome",
    ],
    "surname": [
        "surname", "last name", "last_name", "lastname", "apelido", "sobrenome",
        "family name", "family_name", "familyname", "apelidos"
    ],
    "age": ["age", "idade", "age_years", "age (years)"],
    "birthdate": [
        "birthdate", "birth date", "birth_date", "date of birth", "dob",
        "data de nascimento", "data nascimento", "nascimento", "birthday"
    ],
    "submission_date": [
        "submission date", "submission_date", "submit date", "submit_date",
        "carimbo de data/hora", "carimbo de data hora", "timestamp",
        "data de submissão", "data submissao", "date submitted"
    ],
    "sex": ["sex", "gender", "sexo", "género", "genero"],
    "email": ["email", "e-mail", "mail"],
    "phone": ["phone", "telefone", "tel", "mobile", "telemovel", "telemóvel", "número de telemóvel", "numero de telemovel"],
    "postal_code": ["postal code", "postcode", "zip", "código postal", "codigo postal", "qual o código postal da sua morada"],
    "nationality": ["nationality", "nacionalidade", "country", "country of origin", "país de origem"],
    "agreeableness": ["agreeableness", "agreeablness"],
    "openness_to_experience": ["openness to experience", "opennesstoexperience"],
    "online_questionnaire_id": ["id online questionnaire"],
    "xing_account": ["xing account", "xing"],
}

MANDATORY = ["participant_id"]
RECOMMENDED_ORDER = ["name", "age", "sex", "nationality", "phone", "email"]

# ---------- Smart grouping rules ----------
GROUPING_RULES: Dict[str, Sequence[str]] = {
    "education": [
        r"\beducation\b",
        r"\bhighest\b.*\b(degree|school)\b",
        r"\bn[ií]vel\b.*\bescolar",
        r"\b(escolaridade|grau\b.*escolar)",
        r"\bqual\b.*\bn[ií]vel\b.*\bescolar",
    ],
    "employment_status": [
        r"\b(emprego|situa[cç][aã]o profissional|occupation|employment)\b",
        r"\bqual\b.*\bsitua[cç][aã]o\b.*\bprof",
    ],
    "household_income_net_monthly": [
        r"\bincome\b",
        r"\brendimento\b",
        r"\brendimento.*l[íi]quido\b",
        r"\brendimento\b.*(famili|agregado)",
    ],
    "years_in_lisbon": [
        r"\blisboa|lisbon\b",
        r"\bn[uú]mero\b.*anos.*lisboa",
        r"\btime\b.*living\b.*lisbon",
        r"\bh[áa]\s*quanto\s*tempo\s*vive\s*em\s*lisboa",
    ],
    "years_in_area": [
        r"\bnr?years\b.*area",
        r"\bquantos\b.*anos\b.*(rea|área)",
        r"\byears\b.*(in the area|lived in)",
    ],
    "children_in_household": [
        r"\bcrian[cç]as\b", r"\bchildren\b", r"\bmenores\b.*18",
    ],
    "is_pregnant": [r"\bgr[aá]vida\b", r"\bpossibly\b.*pregnant", r"\best[áa]\b.*gr[aá]vida"],
    "is_breastfeeding": [r"\bamament", r"\bbreastfeeding\b"],
    "smokes": [r"\bfuma\b", r"\bsmok"],
    "smoking_duration": [r"\bh[aá]\s*quanto\s*tempo\s*fuma", r"\bhow\s*long\s*smok"],
    "pulmonary_disease": [r"\bdoen[cç]a\b.*pulmonar|\basma|\bpneumonia|\bpulmonar\b|\blung\b"],
    "blood_pressure_disorder": [r"\bpress[aã]o\b|\bblood\s*pressure\b|\bhipertens"],
    "neurological_psychiatric_disorder_current": [r"\batualmente\b.*(neurol|psiqui|psychi|neuro)\b"],
    "neurological_psychiatric_disorder_past": [r"\bj[áa]\b.*(neurol|psiqui|psychi|neuro)\b"],
    "visual_disorder": [r"\bdistr[bíi]bio\b.*visual|\bvis(ão|ao)\b|\bvision\b"],
    "email": [r"\bemail|e-mail|mail\b"],
    "phone": [r"\btelefone|telem[oó]vel|phone|mobile|tel\b"],
    "postal_code": [r"\bpostal\b|\bpostcode\b|\bzip\b|\bc[oó]digo postal\b"],
    "nationality": [r"\bnacionalidade\b|\bnationality\b"],
    "online_questionnaire_id": [r"\bonline\b.*questionnaire|id online questionnaire\b"],
    "xing_account": [r"\bxing\b"],
    "sex": [r"\bsex\b|\bgender\b|\bsexo\b|\bg[eé]nero\b|\bgenero\b"],
    "name": [r"\bname\b|\bnome\b|\bfull\s*name\b|\bnome\s*completo\b"],
    "age": [r"\bage\b|\bidade\b"],
    "birthdate": [r"\bbirthdate\b|\bbirth.*date\b|\bdata.*nascimento\b|\bnascimento\b|\bdob\b"],
    "submission_date": [r"\bsubmission.*date\b|\bcarimbo.*data\b|\btimestamp\b|\bdata.*submiss\b"],
}

# ---------- Helpers ----------
def _clean_header(h: str) -> str:
    h = (str(h) if h is not None else "").strip().lower()
    h = re.sub(r"\s+", " ", h)
    h = h.replace("-", " ").replace("/", " ").replace("\\", " ")
    h = re.sub(r"[^a-z0-9 ]+", "", h)
    return re.sub(r"\s+", " ", h).strip()

def _alias_to_canonical(col: str) -> str:
    cleaned = _clean_header(col)
    for canonical, variants in ALIASES.items():
        if cleaned in {_clean_header(v) for v in variants}:
            return canonical
    return cleaned

def _standardize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    rename_map = {c: _alias_to_canonical(c) for c in df.columns}
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

def _normalize_participant_id(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    s = re.sub(r"^(subject|sub)[\s_\-]*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    return f"sub-{s}" if s else ""

def _parse_date(date_val) -> datetime | None:
    """Parse various date formats and return datetime object."""
    if pd.isna(date_val):
        return None
    
    date_str = str(date_val).strip()
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
        '%Y/%m/%d', '%d.%m.%Y', '%Y.%m.%d', '%d/%m/%y', '%m/%d/%y',
        '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try pandas to_datetime as fallback
    try:
        return pd.to_datetime(date_str)
    except:
        return None

def _calculate_age(birthdate: datetime, reference_date: datetime = None) -> int | None:
    """Calculate age based on birthdate and reference date."""
    if not birthdate:
        return None
    
    if reference_date is None:
        reference_date = datetime.now()
    
    age = reference_date.year - birthdate.year
    if (reference_date.month, reference_date.day) < (birthdate.month, birthdate.day):
        age -= 1
    
    return max(0, age)

def _consolidate_names(df: pd.DataFrame, src_name: str) -> Tuple[pd.DataFrame, List[str]]:
    """Consolidate name and surname columns into a single name column."""
    df = df.copy()
    notes = []
    
    if "name" in df.columns and "surname" in df.columns:
        # Combine name and surname
        name_series = df["name"].astype(str).fillna("").str.strip()
        surname_series = df["surname"].astype(str).fillna("").str.strip()
        
        combined_names = []
        for name, surname in zip(name_series, surname_series):
            parts = []
            if name and name != "nan" and name != "":
                parts.append(name)
            if surname and surname != "nan" and surname != "":
                parts.append(surname)
            combined_names.append(" ".join(parts).strip())
        
        df["name"] = combined_names
        # Remove surname column to avoid duplication
        df = df.drop(columns=["surname"])
        notes.append(f"{src_name}: consolidated name and surname columns")
    
    elif "surname" in df.columns and "name" not in df.columns:
        # If only surname exists, rename it to name
        df["name"] = df["surname"]
        df = df.drop(columns=["surname"])
        notes.append(f"{src_name}: renamed surname column to name")
    
    return df, notes

def _process_age_and_birthdate(df: pd.DataFrame, src_name: str) -> Tuple[pd.DataFrame, List[str]]:
    """Process birthdate and calculate age, handling submission dates."""
    df = df.copy()
    notes = []
    needs_age_estimation_note = False
    
    if "birthdate" in df.columns:
        # Parse birthdates
        birthdates = df["birthdate"].apply(_parse_date)
        
        if "age" not in df.columns:
            df["age"] = None
        
        # Check for submission date
        submission_dates = None
        if "submission_date" in df.columns:
            submission_dates = df["submission_date"].apply(_parse_date)
        
        # Calculate ages
        calculated_ages = []
        for i, birthdate in enumerate(birthdates):
            if birthdate is None:
                calculated_ages.append(df["age"].iloc[i] if "age" in df.columns else None)
                continue
            
            if submission_dates is not None and submission_dates.iloc[i] is not None:
                # Use submission date as reference
                age = _calculate_age(birthdate, submission_dates.iloc[i])
                calculated_ages.append(age)
            else:
                # Use today as reference
                age = _calculate_age(birthdate)
                calculated_ages.append(age)
                needs_age_estimation_note = True
        
        # Update age column with calculated values where available
        for i, calc_age in enumerate(calculated_ages):
            if calc_age is not None:
                df.loc[i, "age"] = calc_age
        
        notes.append(f"{src_name}: calculated age from birthdate for available records")
        
        # Remove birthdate column to keep output clean
        df = df.drop(columns=["birthdate"])
        
        # Add estimation note if needed
        if needs_age_estimation_note:
            df["age_estimation_note"] = df.apply(
                lambda row: "Age estimated relative to current date" 
                if pd.notna(row.get("age")) and "submission_date" not in df.columns 
                else None, axis=1
            )
            notes.append(f"{src_name}: added age estimation notes for records calculated relative to today")
    
    # Clean up submission_date if it was only used for age calculation
    if "submission_date" in df.columns and "birthdate" not in df.columns:
        # Keep submission_date as it might be useful metadata
        pass
    
    return df, notes

def _first_nonempty_sheet(path: Path) -> pd.DataFrame:
    try:
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            if not df.empty:
                return df
        return pd.DataFrame()
    except Exception:
        try:
            df = pd.read_excel(path, engine="odf")
            return df if not df.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

def _read_delimited(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding=enc)
            if df.empty:
                continue
            return df
        except Exception:
            continue
    return pd.DataFrame()

ALLOWED_EXTS = {".xlsx", ".xls", ".ods", ".csv", ".tsv", ".txt"}

def load_tabular_any(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls", ".ods"}:
        return _first_nonempty_sheet(path)
    if ext in {".csv", ".tsv", ".txt"}:
        return _read_delimited(path)
    return _read_delimited(path)

# --- gender normalization ---
_GENDER_MAP = {
    # female
    "f": "female", "fem": "female", "female": "female",
    "feminino": "female", "feminina": "female", "mulher": "female", "woman": "female",
    # male
    "m": "male", "masc": "male", "male": "male",
    "masculino": "male", "masculina": "male", "homem": "male", "man": "male",
    # non-binary and variants
    "nonbinary": "non-binary", "non-binary": "non-binary", "nb": "non-binary",
    "não binário": "non-binary", "nao binario": "non-binary", "genderqueer": "non-binary",
    # prefer not to say / unknown
    "prefer not to say": "prefer-not-to-say", "prefer-not-to-say": "prefer-not-to-say",
    "prefiro nao dizer": "prefer-not-to-say", "prefiro não dizer": "prefer-not-to-say",
    "unknown": "unknown", "na": "unknown", "n/a": "unknown", "": "unknown",
}

def _normalize_sex_value(val) -> str:
    if pd.isna(val):
        return "unknown"
    s = str(val).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return _GENDER_MAP.get(s, s)

# ---------- Mandatory checks (participant_id only) ----------
def _ensure_mandatory(df: pd.DataFrame, src_name: str) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Ensure only 'participant_id' is required.
    Strategy if missing:
      1) Look for explicit aliases in ALIASES['participant_id'] (exact on cleaned header).
      2) Look for substring/word matches of the aliases on cleaned headers.
      3) Fallback regex: headers containing whole words id/subject/sub.
    """
    df = df.copy()
    warnings: List[str] = []
    missing = [c for c in MANDATORY if c not in df.columns]

    if "participant_id" in missing:
        # 1) explicit alias exact match on cleaned header
        cleaned_aliases = {_clean_header(a) for a in ALIASES.get("participant_id", [])}
        cleaned_cols = {col: _clean_header(col) for col in df.columns}
        exact_hits = [col for col, cc in cleaned_cols.items() if cc in cleaned_aliases]
        if exact_hits:
            chosen = exact_hits[0]
            df["participant_id"] = df[chosen]
            missing.remove("participant_id")
            warnings.append(f"{src_name}: derived participant_id from '{chosen}'")
        else:
            # 2) substring/word match against aliases (safer for participant id)
            alias_tokens = set()
            for a in cleaned_aliases:
                alias_tokens |= set(a.split())
            token_hits = []
            for col, cc in cleaned_cols.items():
                tokens = set(cc.split())
                if ("id" in tokens or "id" in cc) and ({"participant", "participante", "subject"} & tokens or
                                                       "participant" in cc or "participante" in cc or "subject" in cc):
                    token_hits.append(col)
            if token_hits:
                chosen = token_hits[0]
                df["participant_id"] = df[chosen]
                missing.remove("participant_id")
                warnings.append(f"{src_name}: derived participant_id from '{chosen}'")
            else:
                # 3) fallback broad regex
                candidates = [c for c in df.columns if re.search(r"(?:^|_|\b)(id|subject|sub)(?:$|_|\b)", _clean_header(c))]
                if candidates:
                    chosen = candidates[0]
                    df["participant_id"] = df[chosen]
                    missing.remove("participant_id")
                    warnings.append(f"{src_name}: derived participant_id from '{chosen}'")
                else:
                    warnings.append(f"{src_name}: missing participant_id and no plausible ID column found")

    return df, [m for m in MANDATORY if m not in df.columns], warnings

def _coalesce_columns(df: pd.DataFrame, rules: Dict[str, Sequence[str]]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create canonical columns by coalescing values from columns that match rule patterns.
    Original columns are preserved. Uses combine_first to avoid FutureWarnings.
    """
    df = df.copy()
    notes: List[str] = []
    norm_headers = {col: _clean_header(col) for col in df.columns}

    for canonical, patterns in rules.items():
        if canonical in {"participant_id", "filepath"}:
            continue
        regexes = [re.compile(p) for p in patterns]
        candidates = [col for col, clean in norm_headers.items() if any(r.search(clean) for r in regexes)]
        if not candidates:
            continue

        # Ensure canonical exists and is object dtype
        if canonical not in df.columns:
            df[canonical] = pd.NA
        df[canonical] = df[canonical].astype("object")

        before_nonnull = df[canonical].notna().sum()
        for col in candidates:
            # ensure candidate is object
            df[col] = df[col].astype("object")
            # Avoid deprecated downcasting warning: use combine_first
            df[canonical] = df[canonical].combine_first(df[col])
        after_nonnull = df[canonical].notna().sum()

        if after_nonnull > before_nonnull:
            notes.append(f"Grouped {len(candidates)} column(s) into '{canonical}': {candidates}")

    return df, notes

def _nonempty_count(series: pd.Series) -> int:
    s_str = series.astype(str)
    return int(((series.notna()) & (s_str.str.strip() != "")).sum())

# ---------- Merge core ----------
def merge_participant_excels(
    input_paths: Iterable[Path],
    output_path: Path,
    sheet_name: str = "participants",
    smart_group: bool = True,
) -> pd.DataFrame:
    input_paths = [Path(p) for p in input_paths]
    frames: List[pd.DataFrame] = []
    problems: List[str] = []
    notes: List[str] = []

    for p in input_paths:
        try:
            if not p.exists():
                problems.append(f"{p} : file not found")
                continue
            if p.suffix.lower() not in ALLOWED_EXTS:
                problems.append(f"{p.name}: skipped (unsupported extension)")
                continue

            df = load_tabular_any(p)
            if df.empty:
                problems.append(f"{p.name}: empty/unreadable data")
                continue

            df = df.dropna(how="all")
            if df.empty:
                problems.append(f"{p.name}: only empty rows")
                continue

            # Standardize headers (aliases & typos)
            df = _standardize_headers(df)

            # Consolidate names (merge surname with name)
            df, name_notes = _consolidate_names(df, p.name)
            notes.extend(name_notes)

            # Process age and birthdate
            df, age_notes = _process_age_and_birthdate(df, p.name)
            notes.extend(age_notes)

            # Ensure mandatory participant_id (derive if possible)
            df, missing, warns = _ensure_mandatory(df, p.name)
            notes.extend(warns)
            if "participant_id" in missing:
                problems.append(f"{p.name}: cannot find/derive 'participant_id' -> skipping file")
                continue

            # Normalize participant_id
            df["participant_id"] = df["participant_id"].apply(_normalize_participant_id)

            # Drop rows without valid participant_id after normalization
            before = len(df)
            df = df[df["participant_id"].astype(str).str.len() > 0]
            dropped = before - len(df)
            if dropped > 0:
                notes.append(f"{p.name}: dropped {dropped} row(s) without valid participant_id")
            if df.empty:
                problems.append(f"{p.name}: no valid rows after participant_id normalization")
                continue

            # Normalize recommended fields if present
            if "name" in df.columns:
                df["name"] = df["name"].astype(str).fillna("").str.strip()
            if "sex" in df.columns:
                df["sex"] = df["sex"].map(_normalize_sex_value)

            # Provenance
            df["source_file"] = p.name
            try:
                df["filepath"] = str(p.resolve())
            except Exception:
                df["filepath"] = str(p)

            # Smart grouping (adds canonical columns; originals preserved)
            if smart_group:
                df, grouped_notes = _coalesce_columns(df, GROUPING_RULES)
                notes.extend(grouped_notes)

            # Normalize dtypes to 'object' to keep concat quiet and consistent
            df = df.astype("object")

            frames.append(df)

        except Exception as e:
            problems.append(f"{p.name}: {type(e).__name__}: {e}")

    if not frames:
        details = "\n".join(problems + notes)
        raise RuntimeError("No valid participant rows found in the supplied files.\n" + details)

    # Column union preserving first-seen order
    all_cols: List[str] = []
    for f in frames:
        for c in f.columns:
            if c not in all_cols:
                all_cols.append(c)

    # Reindex frames to union and concat
    frames = [f.reindex(columns=all_cols) for f in frames if not f.empty and f.shape[1] > 0]
    frames = [f.astype("object") for f in frames]
    merged = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()

    # Final sanity
    ok_mask = merged["participant_id"].fillna("").map(lambda x: str(x).startswith("sub-"))
    if not ok_mask.all():
        bad = int((~ok_mask).sum())
        problems.append(f"{bad} row(s) with invalid participant_id in merged output")

    # Column ordering:
    # 1) participant_id
    # 2) recommended: name, age, sex (if present)
    # 3) filepath
    # 4) others by non-empty count desc, then alphabetical
    # 5) age_estimation_note at the end if present
    priority = ["participant_id"] + [c for c in RECOMMENDED_ORDER if c in merged.columns] + ["filepath"]
    priority = [c for c in priority if c in merged.columns]

    remaining = [c for c in merged.columns if c not in priority and c != "age_estimation_note"]
    remaining_sorted = sorted(
        remaining,
        key=lambda col: (_nonempty_count(merged[col]), col.lower()),
        reverse=True,
    )
    
    final_cols = priority + remaining_sorted
    if "age_estimation_note" in merged.columns:
        final_cols.append("age_estimation_note")
    
    merged = merged.reindex(columns=final_cols)

    # Write Excel
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        merged.to_excel(writer, index=False, sheet_name=sheet_name)

    if notes:
        print("Notes:")
        for msg in notes:
            print("  -", msg)
    if problems:
        print("Completed with warnings:")
        for msg in problems:
            print("  -", msg)

    return merged

# ---------- CLI ----------
def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Merge participant tabular files (.xlsx, .xls, .ods, .csv, .tsv, .txt) into a single Excel."
    )
    ap.add_argument("inputs", nargs="+", help="One or more input files (mixed formats allowed).")
    ap.add_argument("-o", "--output", required=True, help="Path to the output .xlsx file.")
    ap.add_argument("-s", "--sheet", default="participants", help="Output sheet name (default: participants).")
    ap.add_argument("--no-smart-group", action="store_true", help="Disable smart grouping of similar columns.")
    return ap.parse_args(argv)

def main():
    args = _parse_args()
    in_paths = [Path(p) for p in args.inputs]
    out_path = Path(args.output)
    merge_participant_excels(in_paths, out_path, sheet_name=args.sheet, smart_group=not args.no_smart_group)
    print(f"✅ Merged {len(in_paths)} file(s) → {out_path}")

if __name__ == "__main__":
    main()