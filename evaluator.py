from typing import Any, Callable, Optional
import sys
from calc_ast import (
    ASTNode, NumberNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    AssignmentNode, FunctionCallNode, FunctionDefNode, OperatorDeclareNode,
    BlockNode, OperatorTable, Associativity, TernaryIfNode
)
from scope import Scope, FunctionValue
from tokenizer import Token


MAX_RECURSION_DEPTH = 500


class EvaluationError(Exception):
    def __init__(self, message: str, token: Token = None):
        self.token = token
        if token:
            message = f"{message} at line {token.line}, column {token.column}"
        super().__init__(message)


class RecursionLimitError(EvaluationError):
    pass


class DivideByZeroError(EvaluationError):
    pass


class ArityMismatchError(EvaluationError):
    pass


class UndefinedNameError(EvaluationError):
    pass


class UndefinedOperatorError(EvaluationError):
    pass


class Evaluator:
    def __init__(self, op_table: OperatorTable, builtin_functions: dict = None,
                 on_operator_declared: Callable[[str, Callable], None] = None):
        self.op_table = op_table
        self.global_scope = Scope(name="global")
        self.current_scope = self.global_scope
        self._on_operator_declared = on_operator_declared
        self._recursion_depth = 0
        self._max_recursion = MAX_RECURSION_DEPTH
        self._init_builtins(builtin_functions or {})

    def _init_builtins(self, builtin_funcs: dict):
        default_builtins = {
            'print': self._builtin_print,
            'abs': self._builtin_abs,
            'sqrt': self._builtin_sqrt,
            'pow': self._builtin_pow,
            'max': self._builtin_max,
            'min': self._builtin_min,
        }
        default_builtins.update(builtin_funcs)
        for name, func in default_builtins.items():
            self.global_scope.variables[name] = func

    def _builtin_print(self, *args):
        print(*args)
        return args[0] if args else None

    def _builtin_abs(self, x):
        return abs(x)

    def _builtin_sqrt(self, x):
        return x ** 0.5

    def _builtin_pow(self, x, y):
        return x ** y

    def _builtin_max(self, *args):
        return max(args)

    def _builtin_min(self, *args):
        return min(args)

    def set_max_recursion(self, depth: int):
        self._max_recursion = depth

    def _enter_call(self, func_name: str):
        self._recursion_depth += 1
        if self._recursion_depth > self._max_recursion:
            raise RecursionLimitError(
                f"Recursion depth exceeded maximum ({self._max_recursion}) "
                f"while calling '{func_name}'"
            )

    def _exit_call(self):
        self._recursion_depth -= 1

    def evaluate(self, node: ASTNode) -> Any:
        method = f'eval_{type(node).__name__}'
        evaluator = getattr(self, method, self.eval_default)
        return evaluator(node)

    def eval_default(self, node: ASTNode) -> Any:
        raise EvaluationError(f"Unknown AST node type: {type(node).__name__}")

    def eval_BlockNode(self, node: BlockNode) -> Any:
        result = None
        for stmt in node.statements:
            result = self.evaluate(stmt)
        return result

    def eval_NumberNode(self, node: NumberNode) -> float:
        return node.value

    def eval_IdentifierNode(self, node: IdentifierNode) -> Any:
        try:
            return self.current_scope.lookup_variable(node.name)
        except NameError:
            raise UndefinedNameError(f"Undefined variable '{node.name}'")

    def eval_TernaryIfNode(self, node: TernaryIfNode) -> Any:
        cond = self.evaluate(node.cond)
        if cond:
            return self.evaluate(node.then_expr)
        else:
            return self.evaluate(node.else_expr)

    def eval_BinaryOpNode(self, node: BinaryOpNode) -> Any:
        if node.op == '&&':
            left = self.evaluate(node.left)
            if not left:
                return 0.0
            right = self.evaluate(node.right)
            return 1.0 if right else 0.0
        if node.op == '||':
            left = self.evaluate(node.left)
            if left:
                return 1.0
            right = self.evaluate(node.right)
            return 1.0 if right else 0.0

        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        return self.apply_binary_operator(node.op, left, right)

    def eval_UnaryOpNode(self, node: UnaryOpNode) -> Any:
        operand = self.evaluate(node.operand)
        return self.apply_unary_operator(node.op, operand)

    def eval_AssignmentNode(self, node: AssignmentNode) -> Any:
        value = self.evaluate(node.value)
        self.current_scope.assign_variable(node.name, value)
        return value

    def eval_FunctionDefNode(self, node: FunctionDefNode) -> Any:
        closure = self.current_scope
        func_value = FunctionValue(node.name, node.params, node.body, closure)
        self.current_scope.define_function(node.name, func_value)
        self.current_scope.define_variable(node.name, func_value)
        return func_value

    def eval_FunctionCallNode(self, node: FunctionCallNode) -> Any:
        func = self._lookup_callable(node.name)

        if callable(func) and not isinstance(func, FunctionValue):
            arg_values = [self.evaluate(arg) for arg in node.args]
            return func(*arg_values)

        if isinstance(func, FunctionValue):
            if len(node.args) != len(func.params):
                raise ArityMismatchError(
                    f"Function '{node.name}' expects {len(func.params)} arguments, "
                    f"got {len(node.args)}"
                )

            self._enter_call(node.name)
            try:
                call_scope = func.closure.create_child_scope(f"call_{node.name}")
                for param, arg in zip(func.params, node.args):
                    call_scope.define_variable(param, self.evaluate(arg))
                call_scope.define_variable(node.name, func)

                previous_scope = self.current_scope
                self.current_scope = call_scope
                try:
                    result = self.evaluate(func.body)
                finally:
                    self.current_scope = previous_scope
            finally:
                self._exit_call()
            return result

        raise UndefinedNameError(f"'{node.name}' is not callable")

    def _lookup_callable(self, name: str) -> Any:
        try:
            return self.current_scope.lookup_variable(name)
        except NameError:
            pass
        try:
            return self.current_scope.lookup_function(name)
        except NameError:
            raise UndefinedNameError(f"Undefined function '{name}'")

    def eval_OperatorDeclareNode(self, node: OperatorDeclareNode) -> Any:
        try:
            self.op_table.add_operator(node.symbol, node.precedence, node.associativity)
        except ValueError as e:
            raise EvaluationError(str(e))

        if node.body is not None and node.left_param and node.right_param:
            closure = self.current_scope
            body = node.body
            left_p = node.left_param
            right_p = node.right_param
            op_symbol = node.symbol

            def semantic_func(l_val: Any, r_val: Any) -> Any:
                call_scope = closure.create_child_scope(f"op_{op_symbol}")
                call_scope.define_variable(left_p, l_val)
                call_scope.define_variable(right_p, r_val)
                prev = self.current_scope
                self.current_scope = call_scope
                try:
                    return self.evaluate(body)
                finally:
                    self.current_scope = prev

            if self._on_operator_declared:
                self._on_operator_declared(op_symbol, semantic_func)

        assoc_str = 'left' if node.associativity == Associativity.LEFT else 'right'
        return (
            f"Operator '{node.symbol}' declared "
            f"(prec={node.precedence}, {assoc_str})"
            + (" with semantic" if node.body else "")
        )

    def apply_binary_operator(self, op: str, left: Any, right: Any) -> Any:
        if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
            raise EvaluationError(f"Operator '{op}' requires numeric operands")

        operations = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': self._safe_div,
            '%': self._safe_mod,
            '**': lambda a, b: a ** b,
            '<<': lambda a, b: int(a) << int(b),
            '>>': lambda a, b: int(a) >> int(b),
            '&': lambda a, b: int(a) & int(b),
            '|': lambda a, b: int(a) | int(b),
            '^': lambda a, b: int(a) ^ int(b),
            '==': lambda a, b: 1.0 if a == b else 0.0,
            '!=': lambda a, b: 1.0 if a != b else 0.0,
            '<': lambda a, b: 1.0 if a < b else 0.0,
            '>': lambda a, b: 1.0 if a > b else 0.0,
            '<=': lambda a, b: 1.0 if a <= b else 0.0,
            '>=': lambda a, b: 1.0 if a >= b else 0.0,
        }

        if op in operations:
            return operations[op](left, right)

        raise UndefinedOperatorError(f"Operator '{op}' is not implemented (semantic not defined)")

    def apply_unary_operator(self, op: str, operand: Any) -> Any:
        if not isinstance(operand, (int, float)):
            raise EvaluationError(f"Unary operator '{op}' requires numeric operand")

        operations = {
            '+': lambda x: x,
            '-': lambda x: -x,
            '!': lambda x: 0.0 if x else 1.0,
            '~': lambda x: ~int(x),
        }

        if op in operations:
            return operations[op](operand)

        raise UndefinedOperatorError(f"Unknown unary operator '{op}'")

    def _safe_div(self, a, b):
        if b == 0:
            raise DivideByZeroError("Division by zero")
        return a / b

    def _safe_mod(self, a, b):
        if b == 0:
            raise DivideByZeroError("Modulo by zero")
        return a % b
