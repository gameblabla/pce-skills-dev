#!/usr/bin/env python3
"""Evaluate a bounded arithmetic expression without executing arbitrary code."""

from __future__ import annotations

import argparse
import ast
from fractions import Fraction
import operator
import re
import sys


MAX_BITS = 4096
MAX_EXPONENT = 1024


def _integer(value: Fraction | int) -> int:
    if isinstance(value, Fraction):
        if value.denominator != 1:
            raise ValueError("bitwise operations require an integer result")
        return value.numerator
    return value


def _bounded(value: Fraction | int) -> Fraction | int:
    numerator = value.numerator if isinstance(value, Fraction) else value
    denominator = value.denominator if isinstance(value, Fraction) else 1
    if numerator.bit_length() > MAX_BITS or denominator.bit_length() > MAX_BITS:
        raise ValueError(f"intermediate result exceeds {MAX_BITS} bits")
    return value


def evaluate_node(node: ast.AST) -> Fraction | int:
    if isinstance(node, ast.Expression):
        return evaluate_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return _bounded(node.value)
    if isinstance(node, ast.UnaryOp):
        value = evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return _bounded(-value)
        if isinstance(node.op, ast.Invert):
            return _bounded(~_integer(value))
    if isinstance(node, ast.BinOp):
        left = evaluate_node(node.left)
        right = evaluate_node(node.right)
        if isinstance(node.op, ast.Add):
            return _bounded(left + right)
        if isinstance(node.op, ast.Sub):
            return _bounded(left - right)
        if isinstance(node.op, ast.Mult):
            return _bounded(left * right)
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("division by zero")
            return _bounded(Fraction(left, right))
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ValueError("division by zero")
            return _bounded(_integer(Fraction(left, right).__floor__()))
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise ValueError("modulo by zero")
            return _bounded(left % right)
        if isinstance(node.op, ast.Pow):
            exponent = _integer(right)
            if abs(exponent) > MAX_EXPONENT:
                raise ValueError(f"exponent exceeds {MAX_EXPONENT}")
            if left == 0 and exponent < 0:
                raise ValueError("zero cannot be raised to a negative exponent")
            return _bounded(Fraction(left) ** exponent)
        if isinstance(node.op, ast.LShift):
            shift = _integer(right)
            if shift < 0 or shift > MAX_BITS:
                raise ValueError(f"shift must be between 0 and {MAX_BITS}")
            return _bounded(_integer(left) << shift)
        if isinstance(node.op, ast.RShift):
            shift = _integer(right)
            if shift < 0 or shift > MAX_BITS:
                raise ValueError(f"shift must be between 0 and {MAX_BITS}")
            return _bounded(_integer(left) >> shift)
        if isinstance(node.op, ast.BitAnd):
            return _bounded(_integer(left) & _integer(right))
        if isinstance(node.op, ast.BitOr):
            return _bounded(_integer(left) | _integer(right))
        if isinstance(node.op, ast.BitXor):
            return _bounded(_integer(left) ^ _integer(right))
    raise ValueError(f"unsupported syntax: {ast.dump(node, include_attributes=False)}")


def evaluate(expression: str) -> Fraction | int:
    expression = expression.strip()
    if not expression or len(expression) > 512:
        raise ValueError("expression must contain 1 to 512 characters")
    expression = re.sub(r"(?<![A-Za-z0-9_])\$([0-9A-Fa-f]+)", r"0x\1", expression)
    tree = ast.parse(expression, mode="eval")
    return _bounded(evaluate_node(tree))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression", nargs="?", help="Use operators + - * / // %% ** << >> & | ^ ~ and parentheses")
    args = parser.parse_args()
    expression = args.expression if args.expression is not None else sys.stdin.read()
    try:
        result = evaluate(expression)
    except (SyntaxError, ValueError, ZeroDivisionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if isinstance(result, Fraction) and result.denominator != 1:
        print(f"fraction: {result.numerator}/{result.denominator}")
    else:
        value = int(result)
        print(f"decimal: {value}")
        print(f"hex: 0x{value:X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
