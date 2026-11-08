"""Unit tests for complaint narrative preparation and profiling."""

import pandas as pd
import pytest

from src.nlp.prepare_text import (
    compute_overall_text_stats,
    compute_product_text_stats,
    compute_repeated_narrative_stats,
    count_words,
    detect_redaction,
    normalize_text,
    prepare_text_dataset,
    validate_text_dataset,
)


def test_normalize_text_lowercase_and_whitespace() -> None:
    raw = "  This IS a  TEST\nwith\r\nnewlines   and   tabs.\t "
    normalized = normalize_text(raw)
    assert normalized == "this is a test with newlines and tabs."


def test_normalize_text_masking_placeholder_removal() -> None:
    raw = "Contacted XXXX Bank regarding account XXXXXXXX on XXXX."
    normalized = normalize_text(raw)
    assert normalized == "contacted bank regarding account on ."
    # Verify non-redacted words containing 'x' are preserved
    assert "tax" in normalize_text("paid my tax")
    assert "fox" in normalize_text("the quick brown fox")


def test_normalize_text_preserves_negations_and_financial_terms() -> None:
    raw = "I did NOT authorize this transaction and NEVER received the billing statement."
    normalized = normalize_text(raw)
    assert "did not" in normalized
    assert "never" in normalized
    assert "authorize" in normalized
    assert "transaction" in normalized
    assert "billing statement" in normalized


def test_normalize_text_preserves_numbers_and_punctuation() -> None:
    raw = "I was charged $150.00 fee on 2019-04-12; why was this done?!"
    normalized = normalize_text(raw)
    assert "$150.00" in normalized
    assert "2019-04-12" in normalized
    assert ";" in normalized
    assert "?!" in normalized


def test_normalize_and_count_empty_or_missing_raw_text() -> None:
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("    ") == ""
    assert normalize_text("XXXX XXXXXXXX") == ""

    assert count_words("") == 0
    assert count_words(None) == 0  # type: ignore[arg-type]


def test_deterministic_normalization() -> None:
    sample = "Account XXXX had a balance of $1,234.56 on 03/15/2019. Did not resolve!"
    output1 = normalize_text(sample)
    output2 = normalize_text(sample)
    assert output1 == output2


def test_count_words_and_character_counts() -> None:
    text = "i did not receive my $500 refund."
    assert count_words(text) == 7
    assert len(text) == 33

    empty = ""
    assert count_words(empty) == 0
    assert len(empty) == 0


def test_detect_redaction() -> None:
    assert detect_redaction("My account XXXX was closed.") is True
    assert detect_redaction("XXXXXX reported error.") is True
    assert detect_redaction("No placeholders in this statement.") is False
    assert detect_redaction("") is False
    assert detect_redaction(None) is False
    assert detect_redaction("The fix was approved.") is False


def test_prepare_text_dataset_preserves_identifiers() -> None:
    df_clean = pd.DataFrame(
        {
            "complaint_id": [101, 102, 103],
            "narrative_group_id": ["hash_a", "hash_b", "hash_c"],
            "consumer_complaint_narrative": [
                "Paid XXXX on time.",
                "Never received card.",
                "Incorrect interest rate.",
            ],
        }
    )
    df_text = prepare_text_dataset(df_clean)

    assert df_text["complaint_id"].tolist() == [101, 102, 103]
    assert df_text["narrative_group_id"].tolist() == ["hash_a", "hash_b", "hash_c"]
    assert df_text["has_redaction"].tolist() == [True, False, False]
    assert df_text.loc[0, "text_nlp"] == "paid on time."


def test_repeated_narrative_stats() -> None:
    df_text = pd.DataFrame(
        {
            "complaint_id": list(range(1, 8)),
            "narrative_group_id": ["g1", "g1", "g1", "g2", "g2", "g3", "g4"],
            "text_nlp": ["text"] * 7,
            "character_count": [4] * 7,
            "word_count": [1] * 7,
            "has_redaction": [False] * 7,
        }
    )
    stats = compute_repeated_narrative_stats(df_text)

    assert stats["distinct_groups"] == 4
    assert stats["repeated_groups"] == 2  # g1 (size 3) and g2 (size 2)
    assert stats["records_in_repeated_groups"] == 5
    assert stats["repeated_records_percentage"] == round(100.0 * 5 / 7, 2)
    assert stats["largest_group_size"] == 3


def test_prepare_text_dataset_row_count() -> None:
    df_clean = pd.DataFrame(
        {
            "complaint_id": [1, 2, 3, 4],
            "narrative_group_id": ["h1", "h2", "h3", "h4"],
            "consumer_complaint_narrative": [
                "Statement error.",
                "XXXX",  # Becomes empty string
                "Dispute not resolved.",
                "Fee of $25 charged.",
            ],
        }
    )
    df_text = prepare_text_dataset(df_clean)
    assert len(df_text) == len(df_clean)
    assert df_text.loc[1, "text_nlp"] == ""
    assert df_text.loc[1, "character_count"] == 0
    assert df_text.loc[1, "word_count"] == 0
    assert bool(df_text.loc[1, "has_redaction"]) is True


def test_validate_text_dataset_raises_on_invalid_columns_or_mismatch() -> None:
    df_clean = pd.DataFrame(
        {
            "complaint_id": [1, 2],
            "narrative_group_id": ["h1", "h2"],
            "consumer_complaint_narrative": ["text a", "text b"],
        }
    )
    df_text = prepare_text_dataset(df_clean)

    # Missing column
    df_bad_cols = df_text.drop(columns=["word_count"])
    with pytest.raises(ValueError, match="Output columns mismatch"):
        validate_text_dataset(df_clean, df_bad_cols)

    # Row count mismatch
    df_bad_rows = df_text.iloc[:1]
    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_text_dataset(df_clean, df_bad_rows)

    # Identifier mismatch
    df_bad_id = df_text.copy()
    df_bad_id.loc[0, "complaint_id"] = 999
    with pytest.raises(ValueError, match="complaint_id column does not match"):
        validate_text_dataset(df_clean, df_bad_id)
