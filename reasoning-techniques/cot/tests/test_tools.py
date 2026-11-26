"""Unit tests for Chain-of-Thought mathematical and verification tools."""

import pytest
from cot_agent.tools import calculate, calculate_tool


def test_basic_arithmetic():
    assert calculate("2 + 2") == "4"
    assert calculate("100 - 37") == "63"
    assert calculate("12 * 8") == "96"
    assert calculate("144 / 12") == "12"
    assert calculate("17 // 5") == "3"
    assert calculate("17 % 5") == "2"
    assert calculate("2 ** 8") == "256"


def test_complex_expressions_and_parentheses():
    expr = "(180 * (2 / 5)) + (40 / 2)"
    # 72 + 20 = 92
    assert calculate(expr) == "92"

    expr2 = "((15 * 4) + (20 * 2)) / 5"
    # (60 + 40) / 5 = 20
    assert calculate(expr2) == "20"


def test_math_functions():
    assert calculate("sqrt(144)") == "12"
    assert calculate("abs(-42)") == "42"
    assert calculate("min(10, 5, 20)") == "5"
    assert calculate("max(10, 5, 20)") == "20"
    assert calculate("round(3.14159, 2)") == "3.14"


def test_division_by_zero():
    res = calculate("100 / 0")
    assert "error" in res.lower()
    assert "zero" in res.lower()


def test_disallowed_syntax_and_injection():
    # Attempt arbitrary execution
    res1 = calculate("__import__('os').system('ls')")
    assert "error" in res1.lower()

    res2 = calculate("open('/etc/passwd').read()")
    assert "error" in res2.lower()

    res3 = calculate("x + 5")
    assert "error" in res3.lower()


def test_function_tool_wrapper():
    assert calculate_tool.name == "calculate"
    assert "mathematical expression" in calculate_tool.description.lower()
