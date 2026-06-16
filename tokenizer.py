from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    NUMBER = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    ASSIGN = auto()
    FUN = auto()
    OP_DECLARE = auto()
    LEFT_ASSOC = auto()
    RIGHT_ASSOC = auto()
    QUESTION = auto()
    COLON = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, '{self.value}', {self.line}:{self.column})"


class Tokenizer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def peek(self, offset: int = 0) -> Optional[str]:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def skip_whitespace(self):
        while self.peek() and self.peek().isspace():
            self.advance()

    def skip_comment(self):
        if self.peek() == '#' and self.peek(1) == '!':
            while self.peek() and self.peek() != '\n':
                self.advance()

    def read_number(self) -> Token:
        start_col = self.column
        start_pos = self.pos
        has_dot = False
        while self.peek() and (self.peek().isdigit() or (self.peek() == '.' and not has_dot)):
            if self.peek() == '.':
                has_dot = True
            self.advance()
        value = self.source[start_pos:self.pos]
        return Token(TokenType.NUMBER, value, self.line, start_col)

    def read_identifier(self) -> Token:
        start_col = self.column
        start_pos = self.pos
        while self.peek() and (self.peek().isalnum() or self.peek() == '_'):
            self.advance()
        value = self.source[start_pos:self.pos]
        keyword_map = {
            'fun': TokenType.FUN,
            'op': TokenType.OP_DECLARE,
            'left': TokenType.LEFT_ASSOC,
            'right': TokenType.RIGHT_ASSOC,
        }
        token_type = keyword_map.get(value, TokenType.IDENTIFIER)
        return Token(token_type, value, self.line, start_col)

    def read_operator(self) -> Token:
        start_col = self.column
        start_pos = self.pos
        op_chars = '+-*/%^&|~<>!=@#$.'
        while self.peek() and self.peek() in op_chars:
            self.advance()
        value = self.source[start_pos:self.pos]
        if value == '=':
            return Token(TokenType.ASSIGN, value, self.line, start_col)
        return Token(TokenType.OPERATOR, value, self.line, start_col)

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()
            self.skip_comment()
            if self.pos >= len(self.source):
                break

            ch = self.peek()
            if ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
            elif ch == '(':
                self.tokens.append(Token(TokenType.LPAREN, ch, self.line, self.column))
                self.advance()
            elif ch == ')':
                self.tokens.append(Token(TokenType.RPAREN, ch, self.line, self.column))
                self.advance()
            elif ch == ',':
                self.tokens.append(Token(TokenType.COMMA, ch, self.line, self.column))
                self.advance()
            elif ch == '?':
                self.tokens.append(Token(TokenType.QUESTION, ch, self.line, self.column))
                self.advance()
            elif ch == ':':
                self.tokens.append(Token(TokenType.COLON, ch, self.line, self.column))
                self.advance()
            else:
                self.tokens.append(self.read_operator())

        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens
