#!/usr/bin/env python3
"""
Expression parser: infix with +, -, *, /, parentheses → RPN (reverse Polish notation).
Tokenize, shunting-yard to RPN, evaluate RPN.
"""
import operator
from typing import List, Union

Token = Union[int, str]


def tokenize(expr: str) -> List[Token]:
    """Tokenize expression: integers and operators + - * / ( ). Ignores whitespace."""
    tokens: List[Token] = []
    expr = expr.strip()
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        if expr[i].isdigit():
            j = i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            tokens.append(int(expr[i:j]))
            i = j
            continue
        if expr[i] in "+-*/()":
            tokens.append(expr[i])
            i += 1
            continue
        raise ValueError(f"Unexpected character at position {i}: {expr[i]!r}")
    return tokens


def to_rpn(tokens: List[Token]) -> List[Token]:
    """Convert infix tokens to reverse Polish notation (shunting-yard)."""
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
    output: List[Token] = []
    op_stack: List[str] = []

    for t in tokens:
        if isinstance(t, int):
            output.append(t)
        elif t == "(":
            op_stack.append(t)
        elif t == ")":
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            if not op_stack or op_stack[-1] != "(":
                raise ValueError("Mismatched parentheses")
            op_stack.pop()
        elif t in "+-*/":
            while (
                op_stack
                and op_stack[-1] != "("
                and precedence.get(op_stack[-1], 0) >= precedence[t]
            ):
                output.append(op_stack.pop())
            op_stack.append(t)
        else:
            raise ValueError(f"Unknown token: {t}")

    while op_stack:
        top = op_stack.pop()
        if top == "(":
            raise ValueError("Mismatched parentheses")
        output.append(top)

    return output


def rpn_to_string(rpn: List[Token]) -> str:
    """Serialize RPN as space-separated tokens."""
    return " ".join(str(t) for t in rpn)


def rpn_from_string(s: str) -> List[Token]:
    """Parse space-separated RPN string into tokens (ints and op chars)."""
    tokens: List[Token] = []
    for part in s.split():
        if part in "+-*/":
            tokens.append(part)
        else:
            tokens.append(int(part))
    return tokens


def evaluate_rpn(rpn: List[Token]) -> int:
    """Evaluate RPN; uses integer division (like Python //) for /."""
    stack: List[int] = []
    ops = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.floordiv,
    }
    for t in rpn:
        if isinstance(t, int):
            stack.append(t)
        else:
            if len(stack) < 2:
                raise ValueError("Not enough operands for operator")
            b, a = stack.pop(), stack.pop()
            stack.append(ops[t](a, b))
    if len(stack) != 1:
        raise ValueError("Invalid RPN expression")
    return stack[0]


def expr_to_rpn_string(expr: str) -> str:
    """Parse infix expression and return RPN as string."""
    return rpn_to_string(to_rpn(tokenize(expr)))


def expr_to_value(expr: str) -> int:
    """Parse infix expression and return its integer value."""
    return evaluate_rpn(to_rpn(tokenize(expr)))
