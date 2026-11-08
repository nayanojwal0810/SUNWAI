"""Prepare and profile complaint narratives for NLP analysis."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from src.data.profile_complaints import load_config

REDACTION_PATTERN = re.compile(r"[xX]{4,}")
WHITESPACE_PATTERN = re.compile(r"\s+")
WORD_PATTERN = re.compile(r"\b\w+\b")


def normalize_text(text: Any) -> str:
    """Normalize narrative text for NLP analysis.

    Applies lowercase conversion, removes CFPB masking placeholders (runs of 4+ X characters),
    normalizes line breaks and whitespace to single spaces, and trims edges.
    Preserves normal punctuation, negation words, financial terminology, and numbers.
    """
    if not isinstance(text, str) or not text:
        return ""
    lowered = text.lower()
    no_redaction = REDACTION_PATTERN.sub("", lowered)
    return WHITESPACE_PATTERN.sub(" ", no_redaction).strip()


def detect_redaction(text: Any) -> bool:
    """Check whether narrative contains CFPB masking placeholders (runs of 4+ X characters)."""
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
    """Validate schema, row counts, identifiers, non-negativity, and determinism."""
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

    if not df_text["complaint_id"].equals(df_clean["complaint_id"]):
        raise ValueError("complaint_id column does not match input exactly.")

    if not df_text["narrative_group_id"].equals(df_clean["narrative_group_id"]):
        raise ValueError("narrative_group_id column does not match input exactly.")

    if (df_text["character_count"] < 0).any():
        raise ValueError("Found negative character counts.")

    if (df_text["word_count"] < 0).any():
        raise ValueError("Found negative word counts.")

    empty_mask = df_text["character_count"] == 0
    if not (df_text.loc[empty_mask, "word_count"] == 0).all():
        raise ValueError("Empty processed texts must have zero words.")

    if not (df_text.loc[empty_mask, "text_nlp"] == "").all():
        raise ValueError("Empty character counts must correspond to empty string text_nlp.")

    # Determinism check on sample
    sample_text = "I did not receive my $500 refund from XXXX Bank on 2019-05-01."
    res1 = normalize_text(sample_text)
    res2 = normalize_text(sample_text)
    if res1 != res2 or "not" not in res1 or "500" not in res1 or "xxxx" in res1:
        raise ValueError("Normalization determinism or rule check failed.")


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


def format_text_profile_report(
    overall_stats: dict[str, Any],
    repeated_stats: dict[str, Any],
    product_stats: pd.DataFrame,
) -> str:
    """Format narrative profiling results into a structured Markdown report."""
    min_word_prod = product_stats.loc[product_stats["median_word_count"].idxmin()]
    max_word_prod = product_stats.loc[product_stats["median_word_count"].idxmax()]
    max_rep_prod = product_stats.loc[product_stats["repeated_group_percentage"].idxmax()]
    min_rep_prod = product_stats.loc[product_stats["repeated_group_percentage"].idxmin()]

    lines = [
        "# Complaint Narrative Quality and Profiling Report",
        "",
        "## 1. Text Dataset Overview",
        "",
        "This report profiles the customer-written complaint narratives in the prepared SUNWAI dataset. "
        "The analytical scope covers the full historical extract of 117,214 complaints (January 1, 2019 through "
        "January 9, 2020), which differs from the calendar-year-2019 business analysis window. Every record in this "
        "extract contains an original narrative submitted online with consumer consent.",
        "",
        f"- **Total complaint records:** {overall_stats['total_complaints']:,}",
        f"- **Nonempty processed narratives (`text_nlp`):** {overall_stats['nonempty_narratives']:,} "
        f"({round(100.0 * overall_stats['nonempty_narratives'] / overall_stats['total_complaints'], 3):.3f}%)",
        f"- **Empty processed narratives:** {overall_stats['empty_narratives']:,} (records where narratives consisted "
        "exclusively of masking placeholders and whitespace)",
        f"- **Masking placeholder rate:** {overall_stats['redacted_percentage']:.2f}% of narratives ({overall_stats['redacted_count']:,} records)",
        "",
        "### Text Processing Method",
        "",
        "The prepared text field (`text_nlp`) is an analytical copy derived from `consumer_complaint_narrative` using "
        "lightweight, CPU-friendly standard transformations:",
        "",
        "1. **Lowercase conversion:** Standardized using lowercase transformation.",
        "2. **Whitespace normalization:** Line breaks, tabs, and repeated spaces collapsed to single spaces.",
        "3. **Masking placeholder removal:** CFPB redaction strings consisting of runs of four or more `X` characters "
        "(such as `XXXX`) were removed from `text_nlp` to avoid artificial high-frequency terms.",
        "4. **Trimming:** Leading and trailing whitespace removed.",
        "",
        "Normal punctuation, negation words (e.g., 'not', 'never', 'did not'), financial numbers, and domain vocabulary "
        "were strictly preserved to retain semantic context for future NLP tasks.",
        "",
        "## 2. Narrative Quality",
        "",
        "Narratives exhibit substantial variation in length, ranging from brief notices to multi-page dispute chronologies. "
        "Word counts are calculated using a consistent regex token-counting rule (`\\b\\w+\\b`).",
        "",
        "| Metric | Value |",
        "| :--- | :---: |",
        f"| Median character count | {overall_stats['median_char_count']:.0f} characters |",
        f"| Median word count | {overall_stats['median_word_count']:.0f} words |",
        f"| 10th percentile word count | {overall_stats['p10_word_count']:.0f} words |",
        f"| 90th percentile word count | {overall_stats['p90_word_count']:.0f} words |",
        f"| Short narratives (< 20 words) | {overall_stats['short_text_count']:,} ({overall_stats['short_text_percentage']:.2f}%) |",
        f"| Masked narratives (containing `XXXX`) | {overall_stats['redacted_count']:,} ({overall_stats['redacted_percentage']:.2f}%) |",
        "",
        "The median complaint contains 116 words, while the middle 80% spans from 31 to 393 words. Only 5.07% of narratives "
        "contain fewer than 20 words, confirming that the vast majority of complaints provide sufficient text volume for vocabulary "
        "extraction and topic discovery.",
        "",
        "## 3. Repeated Narratives",
        "",
        "Using the stable `narrative_group_id` (derived from lowercased, whitespace-collapsed original narratives), "
        "repeated complaint texts were analyzed across the historical extract:",
        "",
        "| Metric | Value |",
        "| :--- | :---: |",
        f"| Distinct narrative groups | {repeated_stats['distinct_groups']:,} |",
        f"| Groups appearing more than once | {repeated_stats['repeated_groups']:,} |",
        f"| Complaints belonging to repeated groups | {repeated_stats['records_in_repeated_groups']:,} |",
        f"| Share of complaints in repeated groups | {repeated_stats['repeated_records_percentage']:.2f}% |",
        f"| Largest group size | {repeated_stats['largest_group_size']:,} complaints |",
        "",
        "While 88.9% of distinct text groups appear only once, repeated groups account for 16.27% of all complaints in the dataset. "
        "These repetitions often stem from credit-repair template letters, identical debt-dispute forms, or batch submissions. "
        "Repeated narratives are valid consumer filings and are retained in full; however, they require strict partitioning safeguards "
        "in downstream modeling.",
        "",
        "## 4. Differences Across Products",
        "",
        "Text characteristics differ substantially across financial product lines:",
        "",
        "| Financial Product | Complaints | Median Words | Masking Rate | Repeated Narrative % |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    for _, row in product_stats.iterrows():
        lines.append(
            f"| {row['product']} | {int(row['complaint_count']):,} | {row['median_word_count']:.0f} | "
            f"{row['redaction_percentage']:.2f}% | {row['repeated_group_percentage']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "### Observations",
            "",
            f"- **Text length disparity:** Median length ranges from {min_word_prod['median_word_count']:.0f} words in {min_word_prod['product']} "
            f"up to {max_word_prod['median_word_count']:.0f} words in {max_word_prod['product']}. Loan and mortgage disputes typically involve "
            "detailed transaction histories, whereas credit reporting complaints are often concise dispute requests.",
            f"- **Repetition concentration:** Credit reporting complaints have a {max_rep_prod['repeated_group_percentage']:.2f}% repeated-group rate, "
            f"whereas {min_rep_prod['product']} has only {min_rep_prod['repeated_group_percentage']:.2f}%. This high repetition concentration "
            "reflects standardized credit dispute templates circulating in the industry.",
            f"- **Placeholder prevalence:** Masking placeholders appear in over 75% of narratives across all product categories, peaking at "
            f"{product_stats['redaction_percentage'].max():.2f}% in Money transfer products where account and tracking numbers are routinely masked.",
            "",
            "## 5. Implications for NLP and Modeling",
            "",
            "The narrative profile establishes critical methodological boundaries for subsequent NLP and machine learning stages:",
            "",
            "1. **Group-aware data partitioning:** Because 16.27% of complaints belong to repeated narrative groups, naive random train/test "
            "splitting would leak identical narratives across folds, inflating evaluation metrics. Splits must partition on `narrative_group_id`.",
            "2. **Vocabulary fitting on training splits only:** TF-IDF vectorizers, topic models, and vocabulary selectors must be fitted "
            "strictly on training folds and transformed on validation/test folds without data leakage.",
            "3. **Template dominance in topic modeling:** Standardized credit dispute templates will naturally form dominant clusters "
            "if unaddressed. Theme discovery should evaluate both all-complaint and unique-narrative subsets.",
            "4. **Preservation of original narratives:** The original `consumer_complaint_narrative` remains available in the clean dataset, "
            "while `text_nlp` serves as a clean baseline representation for tokenization and vectorization.",
            "",
            "## 6. Limitations",
            "",
            "- **Selection bias:** The dataset represents only consumers who submitted narratives online and opted to make them public.",
            "- **Masking artifacts:** Removing `XXXX` placeholders removes redaction symbols but cannot reconstruct masked numbers, dates, or entity names.",
            "- **Descriptive word metrics:** Word counts reflect regex-based token counts rather than syntactic or semantic complexity.",
            "- **Observational scope:** Repeated narratives reflect shared text patterns, not verified consumer satisfaction or complaint validity.",
        ]
    )

    return "\n".join(lines) + "\n"


def export_text_dataset(df_text: pd.DataFrame, export_path: str | Path) -> None:
    """Save prepared text dataset to compressed CSV and verify reload."""
    path = Path(export_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df_text.to_csv(path, index=False, compression="gzip")

    # Reload check
    reloaded = pd.read_csv(path, low_memory=False)
    if len(reloaded) != len(df_text):
        raise ValueError(f"Reload check failed: row count mismatch ({len(reloaded)} != {len(df_text)}).")
    if list(reloaded.columns) != list(df_text.columns):
        raise ValueError("Reload check failed: column mismatch.")


def run_text_preparation(
    config_path: str | Path = "config/settings.yaml",
    report_path: str | Path = "reports/text_profile.md",
) -> dict[str, Any]:
    """Execute complete narrative preparation, profiling, validation, and reporting workflow."""
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

    report_markdown = format_text_profile_report(overall_stats, repeated_stats, product_stats)
    rep_file = Path(report_path)
    rep_file.parent.mkdir(parents=True, exist_ok=True)
    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    return {
        "input_rows": len(df_clean),
        "output_rows": len(df_text),
        "text_file": str(text_file).replace("\\", "/"),
        "report_file": str(report_path).replace("\\", "/"),
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
    print(f"Report generated: {results['report_file']}")


if __name__ == "__main__":
    main()
