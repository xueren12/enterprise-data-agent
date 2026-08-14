from evaluation.cases import build_fallback_cases, build_query_cases
from evaluation.run_evaluation import evaluate, load_gold_cases


def test_evaluation_dataset_has_150_supported_cases():
    cases = build_query_cases()

    assert len(cases) == 150
    assert len({case.case_id for case in cases}) == 150


def test_offline_evaluation_is_reproducible():
    result = evaluate()

    assert result["rule_plan"]["success"] == 150
    assert result["controlled_sql_validation"]["success"] == 150
    assert result["controlled_sql_execution"]["skipped"] is True
    assert result["fallback"]["success"] == len(build_fallback_cases())
    assert result["failures"] == []


def test_llm_gold_dataset_is_manually_labeled_and_diverse():
    cases = load_gold_cases()

    assert len(cases) >= 24
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert len({case["expected_plan"]["intent"] for case in cases}) == 6
