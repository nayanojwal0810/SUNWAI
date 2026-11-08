"""Unit tests for complaint narrative preparation, profiling, and validation."""

from pathlib import Path
import pandas as pd
import pytest

from src.nlp.prepare_text import (
    compute_overall_text_stats,
    compute_product_text_stats,
    compute_repeated_narrative_stats,
    count_words,
    detect_redaction,
    export_text_dataset,
    load_text_dataset,
    normalize_text,
    prepare_text_dataset,
    validate_text_dataset,
)


def test_normalize_text_lowercase_and_whitespace() -> None:
    raw = "  This IS a  TEST\nwith\r\nnewlines   and   tabs.\t "
    normalized = normalize_text(raw)
    assert normalized == "this is a test with newlines and tabs."


def test_redaction_removal_from_standalone_placeholders() -> None:
    assert normalize_text("XXXX") == ""
    assert normalize_text("XXXXXXXX") == ""
    assert normalize_text("Contacted XXXX Bank regarding account XXXXXXXX.") == "contacted bank regarding account ."
    assert normalize_text("Date: XXXX/XX/XX on file.") == "date: /xx/xx on file."
    assert normalize_text("Balance of $XXXX.00 overdue.") == "balance of $.00 overdue."


def test_preservation_of_words_containing_internal_xxxx() -> None:
    assert normalize_text("This is an exxxxample of text.") == "this is an exxxxample of text."
    assert normalize_text("wordXXXX") == "wordxxxx"
    assert normalize_text("XXXXword") == "xxxxword"
    assert normalize_text("paid my tax") == "paid my tax"
    assert normalize_text("the quick brown fox") == "the quick brown fox"


def test_correct_redaction_detection_using_revised_pattern() -> None:
    assert detect_redaction("My account XXXX was closed.") is True
    assert detect_redaction("XXXXXX reported error.") is True
    assert detect_redaction("XXXX1234") is True
    assert detect_redaction("1234XXXX") is True
    assert detect_redaction("exxxxample") is False
    assert detect_redaction("wordXXXX") is False
    assert detect_redaction("XXXXword") is False
    assert detect_redaction("tax") is False
    assert detect_redaction("No placeholders in this statement.") is False
    assert detect_redaction("") is False
    assert detect_redaction(None) is False


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


def test_prepare_text_dataset_row_count_and_empty_text() -> None:
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


def test_empty_strings_survive_export_and_reload(tmp_path: Path) -> None:
    export_file = tmp_path / "test_complaints_text.csv.gz"
    df = pd.DataFrame(
        {
            "complaint_id": [1, 2, 3],
            "narrative_group_id": ["grp_1", "grp_2", "grp_3"],
            "text_nlp": ["valid narrative text", "", "another complaint narrative"],
            "character_count": [20, 0, 27],
            "word_count": [3, 0, 3],
            "has_redaction": [False, True, False],
        }
    )

    export_text_dataset(df, export_file)
    reloaded = load_text_dataset(export_file)

    assert len(reloaded) == 3
    assert reloaded.loc[1, "text_nlp"] == ""
    assert isinstance(reloaded.loc[1, "text_nlp"], str)
    assert not pd.isna(reloaded.loc[1, "text_nlp"])
    assert not reloaded["text_nlp"].isna().any()


def test_distinguish_empty_string_from_missing_value(tmp_path: Path) -> None:
    export_file = tmp_path / "test_na_distinction.csv.gz"
    df = pd.DataFrame(
        {
            "complaint_id": [10],
            "narrative_group_id": ["grp_10"],
            "text_nlp": [""],
            "character_count": [0],
            "word_count": [0],
            "has_redaction": [True],
        }
    )
    export_text_dataset(df, export_file)
    reloaded = load_text_dataset(export_file)

    val = reloaded.loc[0, "text_nlp"]
    assert val == ""
    assert val is not None
    assert not pd.isna(val)
    assert len(val) == 0


def test_exact_preservation_of_saved_text_and_identifiers(tmp_path: Path) -> None:
    export_file = tmp_path / "test_preservation.csv.gz"
    df = pd.DataFrame(
        {
            "complaint_id": [501, 502],
            "narrative_group_id": ["sha256_hash_1", "sha256_hash_2"],
            "text_nlp": ["first dispute detail", "second dispute detail"],
            "character_count": [20, 21],
            "word_count": [3, 3],
            "has_redaction": [False, True],
        }
    )
    export_text_dataset(df, export_file)
    reloaded = load_text_dataset(export_file)

    assert reloaded["complaint_id"].tolist() == [501, 502]
    assert reloaded["narrative_group_id"].tolist() == ["sha256_hash_1", "sha256_hash_2"]
    assert reloaded["text_nlp"].tolist() == ["first dispute detail", "second dispute detail"]
    assert reloaded["character_count"].tolist() == [20, 21]
    assert reloaded["word_count"].tolist() == [3, 3]
    assert reloaded["has_redaction"].tolist() == [False, True]


def test_validation_failure_when_processed_text_modified_incorrectly() -> None:
    df_clean = pd.DataFrame(
        {
            "complaint_id": [1, 2],
            "narrative_group_id": ["h1", "h2"],
            "consumer_complaint_narrative": ["text one", "text two"],
        }
    )
    df_text = prepare_text_dataset(df_clean)

    # 1. Modify text to uppercase
    bad_upper = df_text.copy()
    bad_upper.loc[0, "text_nlp"] = "TEXT ONE"
    with pytest.raises(ValueError, match="uppercase"):
        validate_text_dataset(df_clean, bad_upper)

    # 2. Modify text to have extra whitespace (updating character_count so length check passes)
    bad_spaces = df_text.copy()
    bad_spaces.loc[0, "text_nlp"] = "  text one  "
    bad_spaces.loc[0, "character_count"] = len("  text one  ")
    with pytest.raises(ValueError, match="whitespace"):
        validate_text_dataset(df_clean, bad_spaces)

    # 3. Modify text to a different arbitrary string (with matching character and word counts)
    bad_content = df_text.copy()
    bad_content.loc[0, "text_nlp"] = "corrupted text"
    bad_content.loc[0, "character_count"] = len("corrupted text")
    bad_content.loc[0, "word_count"] = 2
    with pytest.raises(ValueError, match="normalize_text"):
        validate_text_dataset(df_clean, bad_content)


def test_validation_failure_when_counts_or_redaction_incorrect() -> None:
    df_clean = pd.DataFrame(
        {
            "complaint_id": [1],
            "narrative_group_id": ["h1"],
            "consumer_complaint_narrative": ["statement error XXXX."],
        }
    )
    df_text = prepare_text_dataset(df_clean)

    # Bad character count
    bad_chars = df_text.copy()
    bad_chars.loc[0, "character_count"] = 999
    with pytest.raises(ValueError, match="character_count does not match"):
        validate_text_dataset(df_clean, bad_chars)

    # Bad word count
    bad_words = df_text.copy()
    bad_words.loc[0, "word_count"] = 999
    with pytest.raises(ValueError, match="word_count does not match"):
        validate_text_dataset(df_clean, bad_words)

    # Bad redaction indicator
    bad_redaction = df_text.copy()
    bad_redaction.loc[0, "has_redaction"] = False
    with pytest.raises(ValueError, match="has_redaction does not match"):
        validate_text_dataset(df_clean, bad_redaction)


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

    # Duplicate complaint_id
    df_dupe = df_text.copy()
    df_dupe.loc[1, "complaint_id"] = df_dupe.loc[0, "complaint_id"]
    with pytest.raises(ValueError, match="duplicate values"):
        validate_text_dataset(df_clean, df_dupe)


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
    assert stats["repeated_groups"] == 2
    assert stats["records_in_repeated_groups"] == 5
    assert stats["repeated_records_percentage"] == round(100.0 * 5 / 7, 2)
    assert stats["largest_group_size"] == 3

