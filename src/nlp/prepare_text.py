"""Prepare and profile complaint narratives for NLP analysis."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from src.data.profile_complaints import load_config

REDACTION_PATTERN = re.compile(r"(?<![a-zA-Z])[xX]{4,}(?![a-zA-Z])")
WHITESPACE_PATTERN = re.compile(r"\s+")
WORD_PATTERN = re.compile(r"\b\w+\b")


def normalize_text(text: Any) -> str:
    """Normalize narrative text for NLP analysis.

    Applies lowercase conversion, removes CFPB masking placeholders (runs of 4+ X characters
    not immediately adjacent to alphabetic letters), normalizes line breaks and whitespace
    to single spaces, and trims edges.
    Preserves normal punctuation, negation words, financial terminology, and numbers.
    """
    if not isinstance(text, str) or not text:
        return ""
    lowered = text.lower()
    no_redaction = REDACTION_PATTERN.sub("", lowered)
    return WHITESPACE_PATTERN.sub(" ", no_redaction).strip()


def detect_redaction(text: Any) -> bool:
    """Check whether narrative contains CFPB masking placeholders (runs of 4+ X characters not adjacent to letters)."""
    if not isinstance(text, str) or not text:
        return False
    return bool(REDACTION_PATTERN.search(text))


def count_words(text: str) -> int:
    """Count word-like tokens using a consistent alphanumeric word-boundary rule."""
    if not text:
        return 0
    return len(WORD_PATTERN.findall(text))


def prepare_text_dataset(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Create lightly processed text dataset with text-quality metrics."""
    required_cols = {"complaint_id", "narrative_group_id", "consumer_complaint_narrative"}
    missing = required_cols - set(df_clean.columns)
    if missing:
        raise ValueError(f"Input DataFrame missing required columns: {missing}")

    raw_narratives = df_clean["consumer_complaint_narrative"].tolist()
    text_nlp = [normalize_text(t) for t in raw_narratives]
    has_redaction = [detect_redaction(t) for t in raw_narratives]
    char_counts = [len(t) for t in text_nlp]
    word_counts = [len(WORD_PATTERN.findall(t)) for t in text_nlp]

    return pd.DataFrame(
        {
            "complaint_id": df_clean["complaint_id"].values,
            "narrative_group_id": df_clean["narrative_group_id"].values,
            "text_nlp": text_nlp,
            "character_count": char_counts,
            "word_count": word_counts,
            "has_redaction": has_redaction,
        }
    )


def validate_text_dataset(df_clean: pd.DataFrame, df_text: pd.DataFrame) -> None:
    """Validate schema, row counts, identifiers, non-negativity, and transformation consistency."""
    expected_cols = [
        "complaint_id",
        "narrative_group_id",
        "text_nlp",
        "character_count",
        "word_count",
        "has_redaction",
    ]
    if list(df_text.columns) != expected_cols:
        raise ValueError(f"Output columns mismatch. Expected {expected_cols}, got {list(df_text.columns)}")

    if len(df_text) != len(df_clean):
        raise ValueError(f"Row count mismatch: output has {len(df_text)}, input has {len(df_clean)}.")

    # Unique and nonmissing complaint_id
    if not df_text["complaint_id"].is_unique:
        raise ValueError("complaint_id column contains duplicate values.")
    if df_text["complaint_id"].isna().any():
        raise ValueError("complaint_id column contains missing values.")
    if not df_text["complaint_id"].equals(df_clean["complaint_id"]):
        raise ValueError("complaint_id column does not match input exactly.")

    # Nonmissing and preserved narrative_group_id
    if df_text["narrative_group_id"].isna().any():
        raise ValueError("narrative_group_id column contains missing values.")
    if not df_text["narrative_group_id"].equals(df_clean["narrative_group_id"]):
        raise ValueError("narrative_group_id column does not match input exactly.")

    # Character count checks
    if (df_text["character_count"] < 0).any():
        raise ValueError("Found negative character counts.")
    actual_char_counts = [len(t) for t in df_text["text_nlp"]]
    if df_text["character_count"].tolist() != actual_char_counts:
        raise ValueError("character_count does not match actual length of text_nlp.")

    # Word count checks
    if (df_text["word_count"] < 0).any():
        raise ValueError("Found negative word counts.")
    actual_word_counts = [count_words(t) for t in df_text["text_nlp"]]
    if df_text["word_count"].tolist() != actual_word_counts:
        raise ValueError("word_count does not match actual token count of text_nlp.")

    # Redaction flag checks
    expected_redactions = [detect_redaction(t) for t in df_clean["consumer_complaint_narrative"]]
    if df_text["has_redaction"].tolist() != expected_redactions:
        raise ValueError("has_redaction does not match redaction detection on original narratives.")

    # Empty text consistency
    empty_mask = df_text["character_count"] == 0
    if not (df_text.loc[empty_mask, "word_count"] == 0).all():
        raise ValueError("Empty processed texts must have zero words.")
    if not (df_text.loc[empty_mask, "text_nlp"] == "").all():
        raise ValueError("Empty character counts must correspond to empty string text_nlp.")

    # Output text normalization invariants
    texts = df_text["text_nlp"].tolist()
    if any(t != t.lower() for t in texts):
        raise ValueError("Found uppercase characters in text_nlp.")
    if any(t != t.strip() for t in texts):
        raise ValueError("Found unstripped leading or trailing whitespace in text_nlp.")
    if any("\n" in t or "\r" in t or "\t" in t or "  " in t for t in texts):
        raise ValueError("Found uncollapsed whitespace, tabs, or newlines in text_nlp.")
    if any(detect_redaction(t) for t in texts if t):
        raise ValueError("Found unremoved redaction placeholders in text_nlp.")

    # Exact normalization match
    expected_texts = [normalize_text(t) for t in df_clean["consumer_complaint_narrative"]]
    if df_text["text_nlp"].tolist() != expected_texts:
        raise ValueError("text_nlp values do not match expected normalize_text() output.")


def load_text_dataset(path: str | Path) -> pd.DataFrame:
    """Load prepared text dataset preserving empty strings without converting to NaN."""
    return pd.read_csv(
        path,
        keep_default_na=False,
        dtype={
            "complaint_id": "int64",
            "narrative_group_id": "str",
            "text_nlp": "str",
            "character_count": "int64",
            "word_count": "int64",
            "has_redaction": "bool",
        },
    )


def export_text_dataset(df_text: pd.DataFrame, export_path: str | Path) -> None:
    """Save prepared text dataset to compressed CSV and verify reload integrity."""
    path = Path(export_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df_text.to_csv(path, index=False, compression="gzip")

    # Reload check preserving empty strings
    reloaded = load_text_dataset(path)
    if len(reloaded) != len(df_text):
        raise ValueError(f"Reload check failed: row count mismatch ({len(reloaded)} != {len(df_text)}).")
    if list(reloaded.columns) != list(df_text.columns):
        raise ValueError(f"Reload check failed: column mismatch ({list(reloaded.columns)} != {list(df_text.columns)}).")
    if not reloaded["complaint_id"].equals(df_text["complaint_id"]):
        raise ValueError("Reload check failed: complaint_id values changed.")
    if not reloaded["narrative_group_id"].equals(df_text["narrative_group_id"]):
        raise ValueError("Reload check failed: narrative_group_id values changed.")
    if reloaded["text_nlp"].tolist() != df_text["text_nlp"].tolist():
        raise ValueError("Reload check failed: text_nlp values changed.")
    if not reloaded["character_count"].equals(df_text["character_count"]):
        raise ValueError("Reload check failed: character_count values changed.")
    if not reloaded["word_count"].equals(df_text["word_count"]):
        raise ValueError("Reload check failed: word_count values changed.")
    if not reloaded["has_redaction"].equals(df_text["has_redaction"]):
        raise ValueError("Reload check failed: has_redaction values changed.")
    if reloaded["text_nlp"].isna().any():
        raise ValueError("Reload check failed: NaN values introduced in text_nlp.")
    empty_mask = df_text["character_count"] == 0
    if not (reloaded.loc[empty_mask, "text_nlp"] == "").all():
        raise ValueError("Reload check failed: empty text_nlp values not preserved as empty strings.")


def compute_overall_text_stats(df_text: pd.DataFrame) -> dict[str, Any]:
    """Compute aggregate text quality metrics across all complaints."""
    total_records = len(df_text)
    empty_count = int((df_text["character_count"] == 0).sum())
    nonempty_count = total_records - empty_count

    redacted_count = int(df_text["has_redaction"].sum())
    redacted_pct = round(100.0 * redacted_count / total_records, 2) if total_records > 0 else 0.0

    short_count = int((df_text["word_count"] < 20).sum())
    short_pct = round(100.0 * short_count / total_records, 2) if total_records > 0 else 0.0

    return {
        "total_complaints": total_records,
        "nonempty_narratives": nonempty_count,
        "empty_narratives": empty_count,
        "median_char_count": float(df_text["character_count"].median()),
        "median_word_count": float(df_text["word_count"].median()),
        "p10_word_count": float(df_text["word_count"].quantile(0.10)),
        "p90_word_count": float(df_text["word_count"].quantile(0.90)),
        "redacted_count": redacted_count,
        "redacted_percentage": redacted_pct,
        "short_text_count": short_count,
        "short_text_percentage": short_pct,
    }


def compute_repeated_narrative_stats(df_text: pd.DataFrame) -> dict[str, Any]:
    """Compute statistics on repeated complaint narratives using narrative_group_id."""
    total_records = len(df_text)
    group_counts = df_text["narrative_group_id"].value_counts()
    distinct_groups = len(group_counts)
    repeated_groups = int((group_counts > 1).sum())
    records_in_repeated = int(group_counts[group_counts > 1].sum())
    repeated_pct = round(100.0 * records_in_repeated / total_records, 2) if total_records > 0 else 0.0
    max_group_size = int(group_counts.max()) if not group_counts.empty else 0

    return {
        "distinct_groups": distinct_groups,
        "repeated_groups": repeated_groups,
        "records_in_repeated_groups": records_in_repeated,
        "repeated_records_percentage": repeated_pct,
        "largest_group_size": max_group_size,
    }


def compute_product_text_stats(df_clean: pd.DataFrame, df_text: pd.DataFrame) -> pd.DataFrame:
    """Calculate narrative length, redaction, and repetition rates for each financial product."""
    group_counts = df_text["narrative_group_id"].value_counts()
    repeated_group_ids = set(group_counts[group_counts > 1].index)

    merged = pd.DataFrame(
        {
            "product": df_clean["product"].values,
            "word_count": df_text["word_count"].values,
            "has_redaction": df_text["has_redaction"].values,
            "is_repeated": df_text["narrative_group_id"].isin(repeated_group_ids).values,
        }
    )

    stats = (
        merged.groupby("product")
        .agg(
            complaint_count=("word_count", "count"),
            median_word_count=("word_count", "median"),
            redaction_percentage=("has_redaction", lambda x: round(100.0 * x.mean(), 2)),
            repeated_group_percentage=("is_repeated", lambda x: round(100.0 * x.mean(), 2)),
        )
        .reset_index()
        .sort_values(by="complaint_count", ascending=False)
        .reset_index(drop=True)
    )

    return stats


def run_text_preparation(
    config_path: str | Path = "config/settings.yaml",
) -> dict[str, Any]:
    """Prepare text, save it, and return text-quality measurements."""
    config = load_config(config_path)
    clean_file = config.get("data", {}).get("clean_file", "data/processed/complaints_clean.csv.gz")
    text_file = config.get("data", {}).get("text_file", "data/processed/complaints_text.csv.gz")

    clean_path = Path(clean_file)
    if not clean_path.is_file():
        raise FileNotFoundError(f"Cleaned dataset not found: {clean_path}. Run data preparation first.")

    df_clean = pd.read_csv(clean_path, low_memory=False)
    df_text = prepare_text_dataset(df_clean)
    validate_text_dataset(df_clean, df_text)

    export_text_dataset(df_text, text_file)

    overall_stats = compute_overall_text_stats(df_text)
    repeated_stats = compute_repeated_narrative_stats(df_text)
    product_stats = compute_product_text_stats(df_clean, df_text)

    return {
        "input_rows": len(df_clean),
        "output_rows": len(df_text),
        "text_file": str(text_file).replace("\\", "/"),
        "overall_stats": overall_stats,
        "repeated_stats": repeated_stats,
        "product_stats": product_stats,
    }


def main() -> None:
    """CLI entry point for preparing and profiling complaint narratives."""
    results = run_text_preparation()
    overall = results["overall_stats"]
    repeated = results["repeated_stats"]

    print("Complaint narrative preparation completed successfully.")
    print(f"Records processed: {results['output_rows']:,}")
    print(f"Nonempty narratives: {overall['nonempty_narratives']:,} (empty: {overall['empty_narratives']})")
    print(f"Median word count: {overall['median_word_count']:.0f} words (P10: {overall['p10_word_count']:.0f}, P90: {overall['p90_word_count']:.0f})")
    print(f"Redaction rate: {overall['redacted_percentage']:.2f}%")
    print(f"Repeated narratives: {repeated['records_in_repeated_groups']:,} records in {repeated['repeated_groups']:,} groups ({repeated['repeated_records_percentage']:.2f}%)")
    print(f"Output saved to: {results['text_file']}")


if __name__ == "__main__":
    main()
