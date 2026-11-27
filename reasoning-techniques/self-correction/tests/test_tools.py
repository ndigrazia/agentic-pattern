"""Unit tests for Self-Correction text inspection and constraint tools."""

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from self_correction_agent.tools import (
    analyze_text_metrics,
    verify_constraint_checklist,
)


def test_analyze_text_metrics_basic():
    text = "We have new products. They are green and techy. Buy GreenTech Gadgets now!"
    metrics = analyze_text_metrics(text)

    assert metrics["char_count"] == 74  # exact length
    assert metrics["word_count"] > 10
    assert metrics["sentence_count"] == 3
    assert metrics["constraint_satisfied"] is True


def test_analyze_text_metrics_with_character_limits():
    short_text = "🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech"
    metrics = analyze_text_metrics(short_text, max_chars=150)

    assert metrics["char_count"] <= 150
    assert metrics["constraint_satisfied"] is True
    assert "Passes max character limit" in metrics["summary"]

    # When exceeding limit
    long_text = "A" * 155
    failed_metrics = analyze_text_metrics(long_text, max_chars=150)
    assert failed_metrics["constraint_satisfied"] is False
    assert "Exceeds max limit by 5 characters" in failed_metrics["summary"]


def test_verify_constraint_checklist_passed():
    text = "🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech"
    res = verify_constraint_checklist(
        text=text,
        required_keywords=["GreenTech Gadgets", "eco-friendly"],
        forbidden_keywords=["bad", "defective"],
        max_length=150,
    )
    assert res["all_passed"] is True
    assert res["required_keywords"]["passed"] is True
    assert res["forbidden_keywords"]["passed"] is True
    assert res["max_length"]["passed"] is True


def test_verify_constraint_checklist_failed():
    text = "We have new products. They are green and techy. Buy now!"
    res = verify_constraint_checklist(
        text=text,
        required_keywords=["GreenTech Gadgets", "eco-friendly"],
        max_length=50,
    )
    assert res["all_passed"] is False
    assert res["required_keywords"]["passed"] is False
    assert "GreenTech Gadgets" in res["required_keywords"]["missing"]
    assert res["max_length"]["passed"] is False
