import math
import os
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()


def add(a: float, b: float) -> float:
    """Add two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum of a and b.
    """
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The product of a and b.
    """
    return a * b


def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent.

    Args:
        base: The base number.
        exponent: The exponent power.

    Returns:
        base raised to the power of exponent.
    """
    return math.pow(base, exponent)


def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer.

    Args:
        n: Non-negative integer.

    Returns:
        The factorial of n.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    return math.factorial(int(n))


MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")

root_agent = Agent(
    name="math_agent",
    model=MODEL_NAME,
    description="Specialized math and computation agent capable of performing arithmetic, powers, and factorials.",
    instruction="""
    You are a specialized mathematical calculation agent.
    When asked to compute, calculate, or perform math operations:
    - ALWAYS use the appropriate tool (add, multiply, power, factorial).
    - Provide the exact calculation result clearly and concisely.
    """,
    tools=[add, multiply, power, factorial],
)
