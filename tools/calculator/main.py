from agent_framework import tool
import math

@tool
def calculator(expression: str) -> str:
    """
    Safely evaluate a mathematical expression and return the result.
    Supports: +, -, *, /, **, sqrt, pi, e, abs, round, pow
    Examples: '2 ** 10', 'sqrt(144)', '3.14 * 5 ** 2'
    """
    allowed = {
        "sqrt": math.sqrt,
        "pi":   math.pi,
        "e":    math.e,
        "abs":  abs,
        "round": round,
        "pow":  pow,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"Result of `{expression}` = {result}"
    except Exception as exc:
        return f"Error evaluating expression: {exc}"