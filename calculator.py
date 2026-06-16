from typing import Any, Callable, Optional
import sys
from tokenizer import Tokenizer, Token, TokenType
from parser import Parser, ParseError
from evaluator import (
    Evaluator, EvaluationError, RecursionLimitError,
    DivideByZeroError, ArityMismatchError, UndefinedNameError,
    UndefinedOperatorError, IndexError_, TypeError_
)
from calc_ast import OperatorTable, Associativity, OperatorDeclareNode


class OperatorSemanticRegistry:
    def __init__(self):
        self._semantics: dict[str, Callable[[Any, Any], Any]] = {}

    def register(self, symbol: str, func: Callable[[Any, Any], Any]) -> None:
        self._semantics[symbol] = func

    def get(self, symbol: str) -> Optional[Callable[[Any, Any], Any]]:
        return self._semantics.get(symbol)

    def has(self, symbol: str) -> bool:
        return symbol in self._semantics


def format_error_with_source(source: str, line_num: int, col_num: int,
                              message: str, error_type: str = "Error") -> str:
    lines = source.split('\n')
    output_lines = []
    output_lines.append(f"{error_type}: {message}")

    if line_num < 1 or line_num > len(lines):
        return '\n'.join(output_lines)

    display_start = max(0, line_num - 3)
    display_end = min(len(lines), line_num + 2)

    for i in range(display_start, display_end):
        actual_line = i + 1
        prefix = f"  {actual_line:>4} | "
        output_lines.append(prefix + lines[i])
        if actual_line == line_num:
            pointer_col = max(1, col_num)
            padding = ' ' * (len(prefix) + pointer_col - 1)
            output_lines.append(padding + '^~~')

    return '\n'.join(output_lines)


def is_input_incomplete(source: str) -> bool:
    tokens = Tokenizer(source).tokenize()
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    depth_do = 0
    last_meaningful = None
    saw_fun = False
    saw_op = False
    saw_if_block = False
    saw_while = False
    saw_for = False
    saw_in = False
    saw_assign = False

    for i, tok in enumerate(tokens):
        if tok.type == TokenType.EOF:
            continue
        if tok.type == TokenType.LPAREN:
            depth_paren += 1
        elif tok.type == TokenType.RPAREN:
            depth_paren -= 1
        elif tok.type == TokenType.LBRACKET:
            depth_bracket += 1
        elif tok.type == TokenType.RBRACKET:
            depth_bracket -= 1
        elif tok.type == TokenType.LBRACE:
            depth_brace += 1
        elif tok.type == TokenType.RBRACE:
            depth_brace -= 1
        elif tok.type == TokenType.DO:
            depth_do += 1
        elif tok.type == TokenType.END:
            depth_do -= 1
        elif tok.type == TokenType.FUN:
            saw_fun = True
        elif tok.type == TokenType.OP_DECLARE:
            saw_op = True
        elif tok.type == TokenType.IDENTIFIER and tok.value == 'if':
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            if next_tok and next_tok.type != TokenType.LPAREN:
                saw_if_block = True
        elif tok.type == TokenType.WHILE:
            saw_while = True
        elif tok.type == TokenType.FOR:
            saw_for = True
        elif tok.type == TokenType.IN:
            saw_in = True
        elif tok.type == TokenType.ASSIGN:
            saw_assign = True
        last_meaningful = tok

    if depth_paren > 0 or depth_bracket > 0 or depth_brace > 0 or depth_do > 0:
        return True

    if saw_fun and not saw_assign and depth_do == 0:
        if last_meaningful and last_meaningful.type == TokenType.RPAREN:
            return True

    if saw_op and last_meaningful and last_meaningful.type in (
        TokenType.LEFT_ASSOC, TokenType.RIGHT_ASSOC
    ):
        return True

    if saw_if_block and last_meaningful and last_meaningful.type not in (TokenType.END, TokenType.ELSE):
        if depth_do == 0:
            return True

    if saw_while and last_meaningful and last_meaningful.type != TokenType.END:
        if depth_do == 0:
            return True

    if saw_for and saw_in and last_meaningful and last_meaningful.type != TokenType.END:
        if depth_do == 0:
            return True

    if saw_for and not saw_in:
        return True

    return False


class CalculatorEngine:
    def __init__(self):
        self.op_table = OperatorTable()
        self.op_semantics = OperatorSemanticRegistry()
        self.evaluator = Evaluator(
            self.op_table,
            on_operator_declared=self._on_operator_declared
        )
        self._patch_evaluator()
        self._last_source = ""

    def _patch_evaluator(self):
        original_apply = self.evaluator.apply_binary_operator

        def patched_apply(op: str, left: Any, right: Any, node=None) -> Any:
            custom_semantic = self.op_semantics.get(op)
            if custom_semantic is not None:
                return custom_semantic(left, right)
            return original_apply(op, left, right, node)

        self.evaluator.apply_binary_operator = patched_apply

    def _on_operator_declared(self, symbol: str, func: Callable) -> None:
        self.op_semantics.register(symbol, func)

    def define_operator_semantic(self, symbol: str, func: Callable[[Any, Any], Any]) -> None:
        self.op_semantics.register(symbol, func)

    def execute(self, source: str) -> Any:
        self._last_source = source
        tokens = Tokenizer(source).tokenize()
        parser = Parser(tokens, self.op_table)

        last_result = None

        while True:
            try:
                stmt = parser.parse_one_statement()
            except ParseError as e:
                msg = self._format_parse_error(source, e)
                raise SyntaxError(msg) from e

            if stmt is None:
                break

            try:
                last_result = self.evaluator.evaluate(stmt)
            except EvaluationError as e:
                msg = self._format_eval_error(source, e)
                raise RuntimeError(msg) from e

        return last_result

    def _format_parse_error(self, source: str, error: ParseError) -> str:
        token = error.token
        line = token.line if token else 1
        col = token.column if token else 1
        return format_error_with_source(source, line, col, str(error), "SyntaxError")

    def _format_eval_error(self, source: str, error: EvaluationError) -> str:
        line = error.line if error.line else 1
        col = error.col if error.col else 1

        if isinstance(error, RecursionLimitError):
            type_name = "RecursionError"
        elif isinstance(error, DivideByZeroError):
            type_name = "ZeroDivisionError"
        elif isinstance(error, ArityMismatchError):
            type_name = "ArityError"
        elif isinstance(error, UndefinedNameError):
            type_name = "NameError"
        elif isinstance(error, UndefinedOperatorError):
            type_name = "OperatorError"
        elif isinstance(error, IndexError_):
            type_name = "IndexError"
        elif isinstance(error, TypeError_):
            type_name = "TypeError"
        else:
            type_name = "RuntimeError"

        return format_error_with_source(source, line, col, str(error), type_name)

    def declare_operator(self, symbol: str, precedence: int,
                         associativity: str = 'left',
                         semantic: Callable[[Any, Any], Any] = None) -> None:
        assoc = Associativity.LEFT if associativity.lower() == 'left' else Associativity.RIGHT
        try:
            self.op_table.add_operator(symbol, precedence, assoc)
        except ValueError as e:
            raise ValueError(str(e)) from e
        if semantic is not None:
            self.define_operator_semantic(symbol, semantic)

    def get_operator_info(self, symbol: str):
        return self.op_table.get_operator(symbol)

    def list_operators(self):
        ops = sorted(self.op_table._operators.values(),
                     key=lambda x: x.precedence, reverse=True)
        return ops

    def set_max_recursion(self, depth: int):
        self.evaluator.set_max_recursion(depth)

    def reset(self):
        self.op_table = OperatorTable()
        self.op_semantics = OperatorSemanticRegistry()
        self.evaluator = Evaluator(
            self.op_table,
            on_operator_declared=self._on_operator_declared
        )
        self._patch_evaluator()


def _format_result(val):
    if isinstance(val, dict):
        items = []
        for k, v in val.items():
            items.append(f"{k}: {_format_result(v)}")
        return '{' + ', '.join(items) + '}'
    if isinstance(val, list):
        items = []
        for x in val:
            items.append(_format_result(x))
        return '[' + ', '.join(items) + ']'
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def run_repl():
    calc = CalculatorEngine()
    print("Custom Operator Calculator REPL (v3)")
    print("====================================")
    print("Syntax:")
    print("  op <sym>, <prec>, <left/right> (a, b) = <body>  - declare operator with rule")
    print("  fun <name>(<params>) = <body>                    - define function (single-line)")
    print("  fun <name>(<params>) do ... end                  - define function (multi-line)")
    print("  do <stmts> end                                    - block with local scope")
    print("  <cond> ? <then> : <else>                         - ternary conditional")
    print("  [1, 2, 3]                                        - list literal")
    print("  1..10                                            - range")
    print("  map(f, [1,2,3]) | filter(f, lst) | sum(lst)     - list operations")
    print("  <var> = <expr>                                   - assign variable")
    print("  <expr>                                           - evaluate expression")
    print("  # comment                                        - line comment")
    print("REPL: :ops  :reset  :maxrec <n>  :quit")
    print("  Multi-line: type 'do', 'fun f(...) do', '[', '(' then continue on next lines")
    print()

    while True:
        try:
            lines = []
            prompt = ">>> "
            while True:
                line = input(prompt).rstrip()
                lines.append(line)
                text = '\n'.join(lines)
                if not is_input_incomplete(text):
                    break
                prompt = "... "

            source = '\n'.join(lines)
            source_stripped = source.strip()
            if not source_stripped:
                continue
            if source_stripped == ':quit':
                break
            if source_stripped == ':reset':
                calc.reset()
                print("Calculator reset.")
                continue
            if source_stripped == ':ops':
                ops = calc.list_operators()
                print(f"  {'Symbol':>6}  {'Prec':>4}  {'Assoc':>5}  {'Type':>8}  {'Semantic':>8}")
                print("  " + "-" * 45)
                for op in ops:
                    status = "builtin" if op.is_builtin else "user"
                    assoc = "left" if op.associativity == Associativity.LEFT else "right"
                    has_sem = calc.op_semantics.has(op.symbol) or op.is_builtin
                    sem = "yes" if has_sem else "no"
                    print(f"  {op.symbol:>6}  {op.precedence:>4}  {assoc:>5}  {status:>8}  {sem:>8}")
                continue
            if source_stripped.startswith(':maxrec'):
                parts = source_stripped.split()
                if len(parts) == 2:
                    try:
                        n = int(parts[1])
                        calc.set_max_recursion(n)
                        print(f"Max recursion set to {n}")
                    except ValueError:
                        print("Usage: :maxrec <positive_integer>")
                else:
                    print("Usage: :maxrec <positive_integer>")
                continue

            result = calc.execute(source)
            if result is not None:
                if isinstance(result, str) and result.startswith("Operator '"):
                    print(result)
                else:
                    print(_format_result(result))
        except (SyntaxError, RuntimeError, ValueError) as e:
            print(str(e))
        except KeyboardInterrupt:
            print()
            break
        except EOFError:
            print()
            break

    print("Goodbye!")


if __name__ == '__main__':
    run_repl()
