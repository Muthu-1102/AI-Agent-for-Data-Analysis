"""
Unit tests for AnswerMatcher
Verifies numerical tolerances, formatted currency, percentages, negative numbers,
markdown decoration, and categorical text matching.
"""

import pytest
import sys
import os

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from evaluation.harness.answer_matcher import AnswerMatcher

def test_extract_numbers():
    text = "The mean sales was **$1,373.78**, which represents a 25.4% increase over -15.2 points."
    nums = AnswerMatcher.extract_numbers(text)
    assert 1373.78 in nums
    assert 25.4 in nums
    assert 0.254 in nums
    assert -15.2 in nums

def test_extract_large_unformatted_numbers():
    text = "Total sum of sales_amount: 758584.4099999999 and salary: 114155.38 and units: 7522.0"
    nums = AnswerMatcher.extract_numbers(text)
    assert any(abs(n - 758584.41) < 0.01 for n in nums)
    assert any(abs(n - 114155.38) < 0.01 for n in nums)
    assert any(abs(n - 7522.0) < 0.01 for n in nums)

def test_match_numeric_exact():
    matched, cand, reason = AnswerMatcher.match_numeric("The answer is 20.0", 20.0, tolerance=0.01)
    assert matched is True
    assert cand == 20.0

def test_match_numeric_tolerance():
    # 20.005 is within 0.01 of 20.0
    matched, cand, reason = AnswerMatcher.match_numeric("Computed: 20.005", 20.0, tolerance=0.01)
    assert matched is True

def test_match_numeric_fail():
    matched, cand, reason = AnswerMatcher.match_numeric("Computed: 35.0", 20.0, tolerance=0.01)
    assert matched is False
    assert cand == 35.0

def test_match_categorical_success():
    matched, cand, reason = AnswerMatcher.match_categorical("The top department is Engineering with 200 staff", "Engineering")
    assert matched is True
    assert cand == "engineering"

def test_match_categorical_case_insensitive():
    matched, cand, reason = AnswerMatcher.match_categorical("Highest region: north", "North")
    assert matched is True

def test_match_categorical_fail():
    matched, cand, reason = AnswerMatcher.match_categorical("Highest region: East", "North")
    assert matched is False

def test_match_dispatch():
    spec_num = {"type": "numeric", "ground_truth": 100.5, "tolerance": 0.1}
    assert AnswerMatcher.match("Result: 100.48", spec_num)[0] is True

    spec_cat = {"type": "categorical", "ground_truth": "Electronics"}
    assert AnswerMatcher.match("Category: Electronics", spec_cat)[0] is True
