from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Any


class Associativity(Enum):
    LEFT = auto()
    RIGHT = auto()


@dataclass
class OperatorInfo:
    symbol: str
    precedence: int
    associativity: Associativity
    is_builtin: bool = False

    def __repr__(self) -> str:
        assoc = 'L' if self.associativity == Associativity.LEFT else 'R'
        return f"OpInfo('{self.symbol}', prec={self.precedence}, {assoc})"


class OperatorTable:
    def __init__(self):
        self._operators: dict[str, OperatorInfo] = {}
        self._init_builtin_operators()

    def _init_builtin_operators(self):
        builtins = [
            ('||', 1, Associativity.LEFT),
            ('&&', 2, Associativity.LEFT),
            ('|', 3, Associativity.LEFT),
            ('^', 4, Associativity.LEFT),
            ('&', 5, Associativity.LEFT),
            ('==', 6, Associativity.LEFT),
            ('!=', 6, Associativity.LEFT),
            ('<', 7, Associativity.LEFT),
            ('>', 7, Associativity.LEFT),
            ('<=', 7, Associativity.LEFT),
            ('>=', 7, Associativity.LEFT),
            ('<<', 8, Associativity.LEFT),
            ('>>', 8, Associativity.LEFT),
            ('+', 9, Associativity.LEFT),
            ('-', 9, Associativity.LEFT),
            ('*', 10, Associativity.LEFT),
            ('/', 10, Associativity.LEFT),
            ('%', 10, Associativity.LEFT),
            ('**', 12, Associativity.RIGHT),
        ]
        for sym, prec, assoc in builtins:
            self._operators[sym] = OperatorInfo(sym, prec, assoc, is_builtin=True)

    def add_operator(self, symbol: str, precedence: int, associativity: Associativity) -> None:
        if symbol in self._operators and self._operators[symbol].is_builtin:
            raise ValueError(f"Cannot override builtin operator '{symbol}'")
        if precedence < 0 or precedence > 100:
            raise ValueError(f"Precedence must be between 0 and 100, got {precedence}")
        self._operators[symbol] = OperatorInfo(symbol, precedence, associativity, is_builtin=False)

    def get_operator(self, symbol: str) -> Optional[OperatorInfo]:
        return self._operators.get(symbol)

    def has_operator(self, symbol: str) -> bool:
        return symbol in self._operators

    def get_precedence(self, symbol: str) -> int:
        op = self._operators.get(symbol)
        if op is None:
            return -1
        return op.precedence

    def get_associativity(self, symbol: str) -> Associativity:
        op = self._operators.get(symbol)
        if op is None:
            return Associativity.LEFT
        return op.associativity

    def __repr__(self) -> str:
        ops = sorted(self._operators.values(), key=lambda x: x.precedence, reverse=True)
        return f"OperatorTable({len(ops)} operators: {ops})"


@dataclass
class ASTNode:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)


@dataclass
class NumberNode(ASTNode):
    value: float


@dataclass
class IdentifierNode(ASTNode):
    name: str


@dataclass
class BinaryOpNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryOpNode(ASTNode):
    op: str
    operand: ASTNode


@dataclass
class AssignmentNode(ASTNode):
    name: str
    value: ASTNode


@dataclass
class FunctionCallNode(ASTNode):
    name: str
    args: List[ASTNode]


@dataclass
class FunctionDefNode(ASTNode):
    name: str
    params: List[str]
    body: ASTNode


@dataclass
class OperatorDeclareNode(ASTNode):
    symbol: str
    precedence: int
    associativity: Associativity
    left_param: Optional[str] = None
    right_param: Optional[str] = None
    body: Optional[ASTNode] = None


@dataclass
class TernaryIfNode(ASTNode):
    cond: ASTNode
    then_expr: ASTNode
    else_expr: ASTNode


@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode]


@dataclass
class ListNode(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class RangeNode(ASTNode):
    start: ASTNode = None
    end: ASTNode = None


@dataclass
class DoBlockNode(ASTNode):
    statements: List[ASTNode]
    is_local_scope: bool = True


@dataclass
class IndexNode(ASTNode):
    target: ASTNode
    index: ASTNode


@dataclass
class SliceNode(ASTNode):
    target: ASTNode
    start: Optional[ASTNode] = None
    end: Optional[ASTNode] = None


@dataclass
class ForNode(ASTNode):
    var_name: str
    iterable: ASTNode
    body: ASTNode
    accum_var: Optional[str] = None
    accum_init: Optional[ASTNode] = None


@dataclass
class IfBlockNode(ASTNode):
    cond: ASTNode
    then_body: ASTNode
    else_body: Optional[ASTNode] = None


@dataclass
class WhileBlockNode(ASTNode):
    cond: ASTNode
    body: ASTNode


@dataclass
class StringNode(ASTNode):
    value: str


@dataclass
class RecordNode(ASTNode):
    pairs: List[tuple] = field(default_factory=list)


@dataclass
class DotAccessNode(ASTNode):
    target: ASTNode
    field: str


@dataclass
class FieldAssignNode(ASTNode):
    target: ASTNode
    field: str
    value: ASTNode
