from typing import Any, Callable, Optional, List, Tuple
from dataclasses import dataclass
import sys
from calc_ast import (
    ASTNode, NumberNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    AssignmentNode, FunctionCallNode, FunctionDefNode, OperatorDeclareNode,
    BlockNode, OperatorTable, Associativity, TernaryIfNode,
    ListNode, RangeNode, DoBlockNode, IndexNode, SliceNode,
    ForNode, IfBlockNode, WhileBlockNode,
    StringNode, RecordNode, DotAccessNode, FieldAssignNode
)
from scope import Scope, FunctionValue
from tokenizer import Token


@dataclass
class CallFrame:
    func_name: str
    line: int
    col: int


MAX_RECURSION_DEPTH = 500


class EvaluationError(Exception):
    def __init__(self, message: str, node: ASTNode = None):
        self.node = node
        self.line = node.line if node and node.line else 0
        self.col = node.col if node and node.col else 0
        if self.line and self.col:
            message = f"{message} at line {self.line}, column {self.col}"
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


class IndexError_(EvaluationError):
    pass


class TypeError_(EvaluationError):
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
        self._call_stack: List[CallFrame] = []
        self._init_builtins(builtin_functions or {})

    def _init_builtins(self, builtin_funcs: dict):
        default_builtins = {
            'print': self._builtin_print,
            'abs': self._builtin_abs,
            'sqrt': self._builtin_sqrt,
            'pow': self._builtin_pow,
            'max': self._builtin_max,
            'min': self._builtin_min,
            'len': self._builtin_len,
            'sum': self._builtin_sum,
            'map': self._builtin_map,
            'filter': self._builtin_filter,
            'range': self._builtin_range,
            'push': self._builtin_push,
            'head': self._builtin_head,
            'tail': self._builtin_tail,
            'nth': self._builtin_nth,
            'str': self._builtin_str,
            'int': self._builtin_int,
            'type': self._builtin_type,
            'list': self._builtin_list,
            'reduce': self._builtin_reduce,
            'sort': self._builtin_sort,
            'sort_by': self._builtin_sort_by,
            'reverse': self._builtin_reverse,
            'keys': self._builtin_keys,
            'values': self._builtin_values,
            'has_key': self._builtin_has_key,
        }
        default_builtins.update(builtin_funcs)
        for name, func in default_builtins.items():
            self.global_scope.variables[name] = func

    def _builtin_print(self, *args):
        formatted = []
        for a in args:
            if isinstance(a, list):
                formatted.append('[' + ', '.join(self._format_val(x) for x in a) + ']')
            else:
                formatted.append(self._format_val(a))
        print(*formatted)
        return args[0] if len(args) == 1 else list(args)

    def _format_val(self, v):
        if isinstance(v, dict):
            items = []
            for k, val in v.items():
                items.append(f"{k}: {self._format_val(val)}")
            return '{' + ', '.join(items) + '}'
        if isinstance(v, list):
            return '[' + ', '.join(self._format_val(x) for x in v) + ']'
        if isinstance(v, str):
            return f'"{v}"'
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)

    def _builtin_abs(self, x):
        return abs(x)

    def _builtin_sqrt(self, x):
        return x ** 0.5

    def _builtin_pow(self, x, y):
        return x ** y

    def _builtin_max(self, *args):
        if len(args) == 1 and isinstance(args[0], list):
            return max(args[0])
        return max(args)

    def _builtin_min(self, *args):
        if len(args) == 1 and isinstance(args[0], list):
            return min(args[0])
        return min(args)

    def _builtin_len(self, x):
        if isinstance(x, list):
            return len(x)
        if isinstance(x, dict):
            return len(x)
        raise TypeError_("len() expects a list or record")

    def _builtin_sum(self, x):
        if isinstance(x, list):
            return sum(x)
        raise TypeError_("sum() expects a list")

    def _builtin_map(self, func, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("map() expects a list as second argument", node)
        result = []
        for item in lst:
            result.append(self._apply_func(func, [item], node))
        return result

    def _builtin_filter(self, func, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("filter() expects a list as second argument", node)
        result = []
        for item in lst:
            val = self._apply_func(func, [item], node)
            if val:
                result.append(item)
        return result

    def _builtin_range(self, *args):
        if len(args) == 1:
            return list(range(int(args[0])))
        if len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        if len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        raise ArityMismatchError("range() expects 1-3 arguments")

    def _builtin_push(self, lst, item):
        if not isinstance(lst, list):
            raise TypeError_("push() expects a list as first argument")
        return lst + [item]

    def _builtin_head(self, lst):
        if not isinstance(lst, list) or len(lst) == 0:
            raise IndexError_("head() of empty list")
        return lst[0]

    def _builtin_tail(self, lst):
        if not isinstance(lst, list) or len(lst) == 0:
            raise IndexError_("tail() of empty list")
        return lst[1:]

    def _builtin_nth(self, lst, n):
        if not isinstance(lst, list):
            raise TypeError_("nth() expects a list")
        idx = int(n)
        if idx < 0 or idx >= len(lst):
            raise IndexError_(f"nth() index {idx} out of range (len={len(lst)})")
        return lst[idx]

    def _builtin_str(self, x):
        return self._format_val(x)

    def _builtin_int(self, x):
        return int(x)

    def _builtin_type(self, x):
        if isinstance(x, dict):
            return "record"
        if isinstance(x, list):
            return "list"
        if isinstance(x, float):
            return "number"
        if isinstance(x, str):
            return "string"
        if callable(x):
            return "function"
        return "unknown"

    def _builtin_list(self, *args):
        return list(args)

    def _builtin_reduce(self, func, init, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("reduce() expects a list as third argument", node)
        accum = init
        for item in lst:
            accum = self._apply_func(func, [accum, item], node)
        return accum

    def _builtin_sort(self, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("sort() expects a list", node)
        try:
            return sorted(lst)
        except TypeError:
            raise TypeError_("sort() elements must be comparable", node)

    def _builtin_sort_by(self, func, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("sort_by() expects a list as second argument", node)
        decorated = []
        for item in lst:
            key = self._apply_func(func, [item], node)
            decorated.append((key, item))
        decorated.sort(key=lambda x: x[0])
        return [item for _, item in decorated]

    def _builtin_reverse(self, lst, node: ASTNode = None):
        if not isinstance(lst, list):
            raise TypeError_("reverse() expects a list", node)
        return list(reversed(lst))

    def _builtin_keys(self, record, node: ASTNode = None):
        if not isinstance(record, dict):
            raise TypeError_("keys() expects a record", node)
        return list(record.keys())

    def _builtin_values(self, record, node: ASTNode = None):
        if not isinstance(record, dict):
            raise TypeError_("values() expects a record", node)
        return list(record.values())

    def _builtin_has_key(self, record, key, node: ASTNode = None):
        if not isinstance(record, dict):
            raise TypeError_("has_key() expects a record as first argument", node)
        return 1.0 if key in record else 0.0

    def _apply_func(self, func, args, node: ASTNode = None):
        if callable(func) and not isinstance(func, FunctionValue):
            return func(*args)
        if isinstance(func, FunctionValue):
            if len(args) != len(func.params):
                raise ArityMismatchError(
                    f"Function expects {len(func.params)} args, got {len(args)}",
                    node
                )
            self._enter_call(func.name, node)
            try:
                call_scope = func.closure.create_child_scope(f"call_{func.name}")
                for param, arg_val in zip(func.params, args):
                    call_scope.define_variable(param, arg_val)
                call_scope.define_variable(func.name, func)
                prev = self.current_scope
                self.current_scope = call_scope
                try:
                    return self.evaluate(func.body)
                finally:
                    self.current_scope = prev
            finally:
                self._exit_call()
        raise TypeError_(f"Cannot call non-function value", node)

    def set_max_recursion(self, depth: int):
        self._max_recursion = depth

    def _enter_call(self, func_name: str, node: ASTNode = None):
        self._recursion_depth += 1
        line = node.line if node else 0
        col = node.col if node else 0
        self._call_stack.append(CallFrame(func_name, line, col))
        if self._recursion_depth > self._max_recursion:
            last_frames = self._call_stack[-10:]
            stack_lines = []
            for i, frame in enumerate(reversed(last_frames)):
                if frame.line and frame.col:
                    stack_lines.append(f"  #{i} {frame.func_name} at line {frame.line}, column {frame.col}")
                else:
                    stack_lines.append(f"  #{i} {frame.func_name}")
            stack_trace = "\n".join(stack_lines)
            top_frame = self._call_stack[-1]
            raise RecursionLimitError(
                f"Recursion depth exceeded ({self._max_recursion})\nCall stack (most recent first):\n{stack_trace}",
                node
            )

    def _exit_call(self):
        self._recursion_depth -= 1
        if self._call_stack:
            self._call_stack.pop()

    def evaluate(self, node: ASTNode) -> Any:
        try:
            method = f'eval_{type(node).__name__}'
            evaluator = getattr(self, method, self.eval_default)
            return evaluator(node)
        except EvaluationError:
            raise
        except Exception as e:
            raise EvaluationError(f"{type(e).__name__}: {e}", node)

    def eval_default(self, node: ASTNode) -> Any:
        raise EvaluationError(f"Unknown AST node type: {type(node).__name__}", node)

    def eval_BlockNode(self, node: BlockNode) -> Any:
        result = None
        for stmt in node.statements:
            result = self.evaluate(stmt)
        return result

    def eval_DoBlockNode(self, node: DoBlockNode) -> Any:
        if node.is_local_scope:
            block_scope = self.current_scope.create_child_scope("do_block")
            block_scope.is_local_block = True
            prev = self.current_scope
            self.current_scope = block_scope
            try:
                result = None
                for stmt in node.statements:
                    result = self.evaluate(stmt)
                return result
            finally:
                self.current_scope = prev
        else:
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
            raise UndefinedNameError(f"Undefined variable '{node.name}'", node)

    def eval_TernaryIfNode(self, node: TernaryIfNode) -> Any:
        cond = self.evaluate(node.cond)
        if cond:
            return self.evaluate(node.then_expr)
        else:
            return self.evaluate(node.else_expr)

    def eval_ListNode(self, node: ListNode) -> list:
        return [self.evaluate(elem) for elem in node.elements]

    def eval_RangeNode(self, node: RangeNode) -> list:
        start = self.evaluate(node.start)
        end = self.evaluate(node.end)
        if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
            raise TypeError_("Range bounds must be numbers", node)
        return list(range(int(start), int(end)))

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
        if node.op == '+' and self._either_is_list(node):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise TypeError_("List concatenation requires two lists", node)

        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        return self.apply_binary_operator(node.op, left, right, node)

    def _either_is_list(self, node: BinaryOpNode) -> bool:
        if isinstance(node.left, ListNode) or isinstance(node.right, ListNode):
            return True
        if isinstance(node.left, RangeNode) or isinstance(node.right, RangeNode):
            return True
        if isinstance(node.left, IdentifierNode):
            try:
                val = self.current_scope.lookup_variable(node.left.name)
                if isinstance(val, list):
                    return True
            except NameError:
                pass
        if isinstance(node.right, IdentifierNode):
            try:
                val = self.current_scope.lookup_variable(node.right.name)
                if isinstance(val, list):
                    return True
            except NameError:
                pass
        return False

    def eval_UnaryOpNode(self, node: UnaryOpNode) -> Any:
        operand = self.evaluate(node.operand)
        return self.apply_unary_operator(node.op, operand, node)

    def eval_AssignmentNode(self, node: AssignmentNode) -> Any:
        value = self.evaluate(node.value)
        if getattr(self.current_scope, 'is_local_block', False):
            self.current_scope.define_variable(node.name, value)
        else:
            self.current_scope.assign_variable(node.name, value)
        return value

    def eval_FunctionDefNode(self, node: FunctionDefNode) -> Any:
        closure = self.current_scope
        func_value = FunctionValue(node.name, node.params, node.body, closure)
        self.current_scope.define_function(node.name, func_value)
        self.current_scope.define_variable(node.name, func_value)
        return func_value

    def eval_FunctionCallNode(self, node: FunctionCallNode) -> Any:
        func = self._lookup_callable(node.name, node)

        if callable(func) and not isinstance(func, FunctionValue):
            arg_values = [self.evaluate(arg) for arg in node.args]
            try:
                return func(*arg_values)
            except TypeError as e:
                raise ArityMismatchError(
                    f"Function '{node.name}': {e}", node
                )

        if isinstance(func, FunctionValue):
            if len(node.args) != len(func.params):
                raise ArityMismatchError(
                    f"Function '{node.name}' expects {len(func.params)} arguments, "
                    f"got {len(node.args)}", node
                )

            self._enter_call(node.name, node)
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

        raise UndefinedNameError(f"'{node.name}' is not callable", node)

    def _lookup_callable(self, name: str, node: ASTNode = None) -> Any:
        try:
            return self.current_scope.lookup_variable(name)
        except NameError:
            pass
        try:
            return self.current_scope.lookup_function(name)
        except NameError:
            raise UndefinedNameError(f"Undefined function '{name}'", node)

    def eval_OperatorDeclareNode(self, node: OperatorDeclareNode) -> Any:
        try:
            self.op_table.add_operator(node.symbol, node.precedence, node.associativity)
        except ValueError as e:
            raise EvaluationError(str(e), node)

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

    def apply_binary_operator(self, op: str, left: Any, right: Any,
                               node: ASTNode = None) -> Any:
        if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
            raise TypeError_(
                f"Operator '{op}' requires numeric operands, got "
                f"{type(left).__name__} and {type(right).__name__}", node
            )

        try:
            if op == '+':
                return left + right
            if op == '-':
                return left - right
            if op == '*':
                return left * right
            if op == '/':
                if right == 0:
                    raise DivideByZeroError("Division by zero", node)
                return left / right
            if op == '%':
                if right == 0:
                    raise DivideByZeroError("Modulo by zero", node)
                return left % right
            if op == '**':
                return left ** right
            if op == '<<':
                return int(left) << int(right)
            if op == '>>':
                return int(left) >> int(right)
            if op == '&':
                return int(left) & int(right)
            if op == '|':
                return int(left) | int(right)
            if op == '^':
                return int(left) ^ int(right)
            if op == '==':
                return 1.0 if left == right else 0.0
            if op == '!=':
                return 1.0 if left != right else 0.0
            if op == '<':
                return 1.0 if left < right else 0.0
            if op == '>':
                return 1.0 if left > right else 0.0
            if op == '<=':
                return 1.0 if left <= right else 0.0
            if op == '>=':
                return 1.0 if left >= right else 0.0
        except EvaluationError:
            raise
        except Exception as e:
            raise EvaluationError(f"Operator '{op}' failed: {e}", node)

        raise UndefinedOperatorError(f"Operator '{op}' is not implemented (semantic not defined)", node)

    def apply_unary_operator(self, op: str, operand: Any, node: ASTNode = None) -> Any:
        if not isinstance(operand, (int, float)):
            raise TypeError_(f"Unary operator '{op}' requires numeric operand", node)

        operations = {
            '+': lambda x: x,
            '-': lambda x: -x,
            '!': lambda x: 0.0 if x else 1.0,
            '~': lambda x: ~int(x),
        }

        if op in operations:
            return operations[op](operand)

        raise UndefinedOperatorError(f"Unknown unary operator '{op}'", node)

    def eval_IndexNode(self, node: IndexNode) -> Any:
        target = self.evaluate(node.target)
        idx_val = self.evaluate(node.index)
        if isinstance(target, dict):
            if idx_val not in target:
                raise UndefinedNameError(f"Record has no key '{idx_val}'", node)
            return target[idx_val]
        if not isinstance(target, list):
            raise TypeError_("Cannot index non-list/non-record value", node)
        idx = int(idx_val)
        if idx < 0 or idx >= len(target):
            raise IndexError_(f"Index {idx} out of range (len={len(target)})", node)
        return target[idx]

    def eval_SliceNode(self, node: SliceNode) -> Any:
        target = self.evaluate(node.target)
        if not isinstance(target, list):
            raise TypeError_("Cannot slice non-list value", node)
        start = 0
        end = len(target)
        if node.start is not None:
            start = int(self.evaluate(node.start))
        if node.end is not None:
            end = int(self.evaluate(node.end))
        return target[start:end]

    def eval_IfBlockNode(self, node: IfBlockNode) -> Any:
        cond = self.evaluate(node.cond)
        if cond:
            return self.evaluate(node.then_body)
        elif node.else_body is not None:
            return self.evaluate(node.else_body)
        return None

    def eval_WhileBlockNode(self, node: WhileBlockNode) -> Any:
        result = None
        while True:
            cond = self.evaluate(node.cond)
            if not cond:
                break
            result = self.evaluate(node.body)
        return result

    def eval_ForNode(self, node: ForNode) -> Any:
        iterable = self.evaluate(node.iterable)
        if not isinstance(iterable, list):
            raise TypeError_("for loop expects a list", node)

        loop_scope = self.current_scope.create_child_scope("for_loop")
        loop_scope.is_local_block = True
        prev = self.current_scope
        self.current_scope = loop_scope

        result = None
        accum_value = None
        if node.accum_var and node.accum_init:
            accum_value = self.evaluate(node.accum_init)
            loop_scope.define_variable(node.accum_var, accum_value)

        try:
            for item in iterable:
                loop_scope.define_variable(node.var_name, item)
                if node.accum_var:
                    loop_scope.define_variable(node.accum_var, accum_value)
                result = self.evaluate(node.body)
                if node.accum_var:
                    accum_value = loop_scope.lookup_variable(node.accum_var)
        finally:
            self.current_scope = prev

        if node.accum_var:
            return accum_value
        return result

    def eval_StringNode(self, node: StringNode) -> str:
        return node.value

    def eval_RecordNode(self, node: RecordNode) -> dict:
        result = {}
        for key, value_node in node.pairs:
            result[key] = self.evaluate(value_node)
        return result

    def eval_DotAccessNode(self, node: DotAccessNode) -> Any:
        target = self.evaluate(node.target)
        if isinstance(target, dict):
            if node.field not in target:
                raise UndefinedNameError(f"Record has no field '{node.field}'", node)
            return target[node.field]
        raise TypeError_("Cannot access field on non-record value", node)

    def eval_FieldAssignNode(self, node: FieldAssignNode) -> Any:
        target = self.evaluate(node.target)
        if not isinstance(target, dict):
            raise TypeError_("Cannot set field on non-record value", node)
        value = self.evaluate(node.value)
        target[node.field] = value
        return value


