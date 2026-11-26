"""Mathematical and verification tools for Chain-of-Thought (CoT) reasoning."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Union
from google.adk.tools import FunctionTool

# Allowed operators for safe mathematical evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed safe math functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Recursively evaluate an AST expression with whitelisted operations only."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant literal: {node.value!r}")
    elif isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable: {node.id}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero in mathematical expression.")
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval(node.operand)
        return SAFE_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise ValueError(f"Disallowed or unsupported function: {ast.dump(node.func)}")
        func = SAFE_FUNCTIONS[node.func.id]
        args = [_safe_eval(arg) for arg in node.args]
        return func(*args)
    else:
        raise ValueError(f"Unsupported expression syntax: {type(node).__name__}")


def calculate(expression: str) -> str:
    """Safely evaluates a mathematical expression string.

    Supports arithmetic operations (+, -, *, /, //, %, **), parentheses,
    constants (pi, e), and standard math functions (sqrt, abs, round, min, max, ceil, floor, log).

    Args:
        expression: The mathematical expression string (e.g. '(120 * 0.15) + (45 / 3)').

    Returns:
        The evaluated numerical result as a string, or an error message if invalid.
    """
    cleaned = expression.strip()
    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = _safe_eval(parsed)
        # Format clean integer representation if whole number
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 6) if isinstance(result, float) else result)
    except Exception as e:
        return f"Calculation error: {e}"


# Tool wrapper for Google ADK Agent
calculate_tool = FunctionTool(calculate)
