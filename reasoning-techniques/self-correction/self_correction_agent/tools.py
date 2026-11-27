"""Verification and text inspection tools for Self-Correction Reasoning."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from google.adk.tools import FunctionTool


def analyze_text_metrics(
    text: str,
    max_chars: Optional[int] = None,
    min_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Analyzes text metrics such as character count, word count, and constraint compliance.

    Args:
        text: The draft or revised content string to analyze.
        max_chars: Optional maximum character count constraint (e.g. 150 for social media post).
        min_chars: Optional minimum character count constraint.

    Returns:
        Dictionary with character count, word count, sentence count, and constraint compliance status.
    """
    cleaned = text.strip()
    char_count = len(cleaned)
    char_count_no_spaces = len(re.sub(r"\s+", "", cleaned))
    words = re.findall(r"\b\w+\b", cleaned)
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", cleaned) if s.strip()]
    sentence_count = len(sentences)

    compliance = True
    messages: List[str] = []

    if max_chars is not None:
        if char_count <= max_chars:
            messages.append(f"Passes max character limit: {char_count}/{max_chars} chars.")
        else:
            compliance = False
            excess = char_count - max_chars
            messages.append(f"Exceeds max limit by {excess} characters: {char_count}/{max_chars} chars.")

    if min_chars is not None:
        if char_count >= min_chars:
            messages.append(f"Passes min character threshold: {char_count}/{min_chars} chars.")
        else:
            compliance = False
            shortage = min_chars - char_count
            messages.append(f"Under min threshold by {shortage} characters: {char_count}/{min_chars} chars.")

    return {
        "char_count": char_count,
        "char_count_no_spaces": char_count_no_spaces,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "constraint_satisfied": compliance,
        "summary": " | ".join(messages) if messages else f"Length: {char_count} chars, {word_count} words.",
    }


def verify_constraint_checklist(
    text: str,
    required_keywords: Optional[List[str]] = None,
    forbidden_keywords: Optional[List[str]] = None,
    max_length: Optional[int] = None,
) -> Dict[str, Any]:
    """Checks whether the text complies with specified keywords and length rules.

    Args:
        text: The text to evaluate.
        required_keywords: List of words/phrases that must appear (case-insensitive).
        forbidden_keywords: List of words/phrases that must NOT appear (case-insensitive).
        max_length: Optional maximum allowed character length.

    Returns:
        Checklist verification results and summary status.
    """
    lower_text = text.lower()
    checklist: Dict[str, Any] = {}
    all_passed = True

    if required_keywords:
        missing = [kw for kw in required_keywords if kw.lower() not in lower_text]
        checklist["required_keywords"] = {
            "passed": len(missing) == 0,
            "missing": missing,
        }
        if missing:
            all_passed = False

    if forbidden_keywords:
        found_forbidden = [kw for kw in forbidden_keywords if kw.lower() in lower_text]
        checklist["forbidden_keywords"] = {
            "passed": len(found_forbidden) == 0,
            "violations": found_forbidden,
        }
        if found_forbidden:
            all_passed = False

    if max_length is not None:
        length = len(text.strip())
        passed_len = length <= max_length
        checklist["max_length"] = {
            "passed": passed_len,
            "current_length": length,
            "max_allowed": max_length,
        }
        if not passed_len:
            all_passed = False

    checklist["all_passed"] = all_passed
    return checklist


# Tool definitions for Google ADK Agent
analyze_text_metrics_tool = FunctionTool(analyze_text_metrics)
verify_constraint_checklist_tool = FunctionTool(verify_constraint_checklist)
