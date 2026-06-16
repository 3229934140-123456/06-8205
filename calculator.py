from typing import Any, Callable, Optional
from tokenizer import Tokenizer
from parser import Parser, ParseError
from evaluator import Evaluator, EvaluationError
from calc_ast import OperatorTable, Associativity, OperatorDeclareNode


class OperatorSemanticRegistry:
    def __init__(self):
        self._semantics: dict[str, Callable[[Any, Any], Any]] = {}
        self._init_builtin_semantics()

    def _init_builtin_semantics(self):
        pass

    def register(self, symbol: str, func: Callable[[Any, Any], Any]) -> None:
        self._semantics[symbol] = func

    def get(self, symbol: str) -> Optional[Callable[[Any, Any], Any]]:
        return self._semantics.get(symbol)

    def has(self, symbol: str) -> bool:
        return symbol in self._semantics


class CalculatorEngine:
    def __init__(self):
        self.op_table = OperatorTable()
        self.op_semantics = OperatorSemanticRegistry()
        self.evaluator = Evaluator(self.op_table)
        self._patch_evaluator()

    def _patch_evaluator(self):
        original_apply = self.evaluator.apply_binary_operator

        def patched_apply(op: str, left: Any, right: Any) -> Any:
            custom_semantic = self.op_semantics.get(op)
            if custom_semantic is not None:
                return custom_semantic(left, right)
            return original_apply(op, left, right)

        self.evaluator.apply_binary_operator = patched_apply

    def define_operator_semantic(self, symbol: str, func: Callable[[Any, Any], Any]) -> None:
        self.op_semantics.register(symbol, func)

    def execute(self, source: str) -> Any:
        tokens = Tokenizer(source).tokenize()
        parser = Parser(tokens, self.op_table)

        try:
            ast = parser.parse_program()
        except ParseError as e:
            raise SyntaxError(str(e)) from e

        try:
            result = self.evaluator.evaluate(ast)
        except EvaluationError as e:
            raise RuntimeError(str(e)) from e

        return result

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

    def reset(self):
        self.op_table = OperatorTable()
        self.op_semantics = OperatorSemanticRegistry()
        self.evaluator = Evaluator(self.op_table)
        self._patch_evaluator()


def run_repl():
    calc = CalculatorEngine()
    print("Custom Operator Calculator REPL")
    print("================================")
    print("Commands:")
    print("  op <symbol>, <precedence>, <left/right>  - declare operator")
    print("  fun <name>(<params>) = <body>            - define function")
    print("  <var> = <expr>                           - assign variable")
    print("  <expr>                                   - evaluate expression")
    print("  :ops                                     - list all operators")
    print("  :reset                                   - reset calculator")
    print("  :quit                                    - exit REPL")
    print()

    while True:
        try:
            line = input(">>> ").strip()
            if not line:
                continue
            if line == ':quit':
                break
            if line == ':reset':
                calc.reset()
                print("Calculator reset.")
                continue
            if line == ':ops':
                ops = calc.list_operators()
                for op in ops:
                    status = "builtin" if op.is_builtin else "user"
                    assoc = "left" if op.associativity == Associativity.LEFT else "right"
                    print(f"  {op.symbol:>4}  prec={op.precedence:>3}  {assoc:>5}  ({status})")
                continue

            result = calc.execute(line)
            if result is not None:
                if isinstance(result, str) and result.startswith("Operator '"):
                    print(result)
                else:
                    print(result)
        except (SyntaxError, RuntimeError, ValueError) as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print()
            break
        except EOFError:
            print()
            break

    print("Goodbye!")


if __name__ == '__main__':
    run_repl()
