"""Unit tests for complaint dataset preparation and transformation pipeline."""

import pandas as pd
import pytest

from src.data.prepare_complaints import (
    clean_categoricals,
    clean_dates,
    clean_identifiers,
    clean_narratives,
    compute_narrative_hash,
    derive_narrative_group_id,
    derive_reported_relief,
    drop_empty_columns,
    prepare_complaints_data,
)


def test_derive_reported_relief_mapping() -> None:
    df = pd.DataFrame(
        {
            "company_response_to_consumer": [
                "Closed with monetary relief",
                "Closed with non-monetary relief",
                "Closed with explanation",
            ]
        }
    )
    result = derive_reported_relief(df)
    assert result["reported_relief"].tolist() == [1, 1, 0]


def test_derive_reported_relief_untimely_response_missing() -> None:
    df = pd.DataFrame(
        {
            "company_response_to_consumer": [
                "Untimely response",
                "Closed with explanation",
            ]
        }
    )
    result = derive_reported_relief(df)
    assert pd.isna(result["reported_relief"].iloc[0])
    assert result["reported_relief"].iloc[1] == 0


def test_derive_reported_relief_unexpected_category() -> None:
    df = pd.DataFrame(
        {
            "company_response_to_consumer": [
                "Closed with explanation",
                "Unexpected corporate status",
            ]
        }
    )
    with pytest.raises(ValueError, match="Unexpected company response"):
        derive_reported_relief(df)


def test_narrative_group_consistency() -> None:
    text_1 = "This is a disputed account note."
    text_2 = "   THIS  IS  A   disputed ACCOUNT note.   "
    text_3 = "Completely different complaint text."

    hash_1 = compute_narrative_hash(text_1)
    hash_2 = compute_narrative_hash(text_2)
    hash_3 = compute_narrative_hash(text_3)

    assert hash_1 == hash_2
    assert hash_1 != hash_3
    assert pd.isna(compute_narrative_hash(None))
    assert pd.isna(compute_narrative_hash("   "))


def test_clean_identifiers_valid() -> None:
    df = pd.DataFrame({"complaint_id": [1001, 1002, 1003]})
    result = clean_identifiers(df)
    assert result["complaint_id"].dtype == "int64"
    assert len(result) == 3


def test_clean_identifiers_rejects_duplicates() -> None:
    df = pd.DataFrame({"complaint_id": [1001, 1002, 1002]})
    with pytest.raises(ValueError, match="duplicate values"):
        clean_identifiers(df)


def test_clean_identifiers_rejects_missing() -> None:
    df = pd.DataFrame({"complaint_id": [1001, None, 1003]})
    with pytest.raises(ValueError, match="missing values"):
        clean_identifiers(df)


def test_clean_dates_valid_and_invalid() -> None:
    valid_df = pd.DataFrame(
        {
            "date_received": ["2019-01-05", "2019-12-31"],
            "date_sent_to_company": ["2019-01-06", "2020-01-02"],
        }
    )
    result = clean_dates(valid_df)
    assert result["date_received"].tolist() == ["2019-01-05", "2019-12-31"]

    invalid_df = pd.DataFrame(
        {
            "date_received": ["2019-99-99"],
            "date_sent_to_company": ["2019-01-01"],
        }
    )
    with pytest.raises(ValueError, match="invalid or missing dates"):
        clean_dates(invalid_df)


def test_clean_categoricals_whitespace_stripping() -> None:
    df = pd.DataFrame(
        {
            "product": ["  Debt collection  ", "Mortgage"],
            "zip_code": [" 335XX ", "902XX"],
            "tags": [None, " Servicemember "],
        }
    )
    result = clean_categoricals(df)
    assert result["product"].tolist() == ["Debt collection", "Mortgage"]
    assert result["zip_code"].tolist() == ["335XX", "902XX"]
    assert pd.isna(result["tags"].iloc[0])
    assert result["tags"].iloc[1] == "Servicemember"


def test_clean_narratives_preserves_words_and_case() -> None:
    df = pd.DataFrame(
        {
            "consumer_complaint_narrative": [
                "  Account XXXX was charged incorrectly.  ",
            ]
        }
    )
    result = clean_narratives(df)
    assert result["consumer_complaint_narrative"].iloc[0] == "Account XXXX was charged incorrectly."


def test_drop_empty_columns_success_and_error() -> None:
    df_empty = pd.DataFrame({"consumer_disputed": [None, None], "keep_col": [1, 2]})
    res = drop_empty_columns(df_empty, columns=("consumer_disputed",))
    assert "consumer_disputed" not in res.columns
    assert "keep_col" in res.columns

    df_not_empty = pd.DataFrame({"consumer_disputed": [None, True]})
    with pytest.raises(ValueError, match="contains non-null values"):
        drop_empty_columns(df_not_empty, columns=("consumer_disputed",))


def test_prepare_complaints_data_pipeline_preserves_rows() -> None:
    df = pd.DataFrame(
        {
            "complaint_id": [1, 2, 3],
            "date_received": ["2019-01-01", "2019-01-02", "2019-01-03"],
            "date_sent_to_company": ["2019-01-01", "2019-01-02", "2019-01-03"],
            "product": [" Debt collection ", "Mortgage", "Credit card"],
            "sub_product": ["Other", "Fixed", "General"],
            "issue": ["Issue 1", "Issue 2", "Issue 3"],
            "sub_issue": ["Sub 1", "Sub 2", None],
            "consumer_complaint_narrative": ["Narrative A", "Narrative B", "Narrative A"],
            "company_public_response": [None, "Response B", None],
            "company": ["Company A", "Company B", "Company C"],
            "state": ["CA", "NY", "TX"],
            "zip_code": ["900XX", "100XX", "750XX"],
            "tags": [None, "Servicemember", None],
            "consumer_consent_provided": ["Consent provided"] * 3,
            "submitted_via": ["Web"] * 3,
            "company_response_to_consumer": [
                "Closed with explanation",
                "Closed with monetary relief",
                "Untimely response",
            ],
            "timely_response": ["Yes", "Yes", "No"],
            "consumer_disputed": [None, None, None],
        }
    )

    cleaned = prepare_complaints_data(df)
    assert len(cleaned) == 3
    assert len(cleaned.columns) == 19
    assert "consumer_disputed" not in cleaned.columns
    assert "reported_relief" in cleaned.columns
    assert "narrative_group_id" in cleaned.columns
    assert cleaned["reported_relief"].tolist() == [0, 1, pd.NA]
    # Rows 0 and 2 have identical narrative text -> identical group ID
    assert cleaned["narrative_group_id"].iloc[0] == cleaned["narrative_group_id"].iloc[2]
    assert cleaned["narrative_group_id"].iloc[0] != cleaned["narrative_group_id"].iloc[1]

