from typing import Any
from calc_ast import (
    ASTNode, NumberNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    AssignmentNode, FunctionCallNode, FunctionDefNode, OperatorDeclareNode,
    BlockNode, OperatorTable, Associativity
)
from scope import Scope, FunctionValue


class EvaluationError(Exception):
    pass


class Evaluator:
    def __init__(self, op_table: OperatorTable, builtin_functions: dict = None):
        self.op_table = op_table
        self.global_scope = Scope(name="global")
        self.current_scope = self.global_scope
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
            raise EvaluationError(f"Undefined variable '{node.name}'")

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

        if node.name == 'if' and isinstance(func, FunctionValue) and len(func.params) == 3:
            if len(node.args) != 3:
                raise EvaluationError(
                    f"Function 'if' expects 3 arguments, got {len(node.args)}"
                )
            cond_val = self.evaluate(node.args[0])
            if cond_val:
                return self.evaluate(node.args[1])
            else:
                return self.evaluate(node.args[2])

        arg_values = [self.evaluate(arg) for arg in node.args]

        if callable(func):
            return func(*arg_values)

        if isinstance(func, FunctionValue):
            if len(arg_values) != len(func.params):
                raise EvaluationError(
                    f"Function '{node.name}' expects {len(func.params)} arguments, "
                    f"got {len(arg_values)}"
                )

            call_scope = func.closure.create_child_scope(f"call_{node.name}")
            for param, arg_val in zip(func.params, arg_values):
                call_scope.define_variable(param, arg_val)
            call_scope.define_variable(node.name, func)

            previous_scope = self.current_scope
            self.current_scope = call_scope
            try:
                result = self.evaluate(func.body)
            finally:
                self.current_scope = previous_scope
            return result

        raise EvaluationError(f"'{node.name}' is not callable")

    def _lookup_callable(self, name: str) -> Any:
        try:
            return self.current_scope.lookup_variable(name)
        except NameError:
            pass
        try:
            return self.current_scope.lookup_function(name)
        except NameError:
            raise EvaluationError(f"Undefined function '{name}'")

    def eval_OperatorDeclareNode(self, node: OperatorDeclareNode) -> Any:
        try:
            self.op_table.add_operator(node.symbol, node.precedence, node.associativity)
        except ValueError as e:
            raise EvaluationError(str(e))
        return f"Operator '{node.symbol}' declared (prec={node.precedence}, {'left' if node.associativity == Associativity.LEFT else 'right'})"

    def apply_binary_operator(self, op: str, left: Any, right: Any) -> Any:
        if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
            raise EvaluationError(f"Operator '{op}' requires numeric operands")

        operations = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else self._raise_div_zero(),
            '%': lambda a, b: a % b if b != 0 else self._raise_div_zero(),
            '**': lambda a, b: a ** b,
            '<<': lambda a, b: int(a) << int(b),
            '>>': lambda a, b: int(a) >> int(b),
            '&': lambda a, b: int(a) & int(b),
            '|': lambda a, b: int(a) | int(b),
            '^': lambda a, b: int(a) ^ int(b),
            '&&': lambda a, b: 1.0 if (a and b) else 0.0,
            '||': lambda a, b: 1.0 if (a or b) else 0.0,
            '==': lambda a, b: 1.0 if a == b else 0.0,
            '!=': lambda a, b: 1.0 if a != b else 0.0,
            '<': lambda a, b: 1.0 if a < b else 0.0,
            '>': lambda a, b: 1.0 if a > b else 0.0,
            '<=': lambda a, b: 1.0 if a <= b else 0.0,
            '>=': lambda a, b: 1.0 if a >= b else 0.0,
        }

        if op in operations:
            return operations[op](left, right)

        raise EvaluationError(f"Operator '{op}' is not implemented")

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

        raise EvaluationError(f"Unknown unary operator '{op}'")

    def _raise_div_zero(self):
        raise EvaluationError("Division by zero")
