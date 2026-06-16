from typing import List, Optional
from tokenizer import Token, TokenType, Tokenizer
from calc_ast import (
    ASTNode, NumberNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    AssignmentNode, FunctionCallNode, FunctionDefNode, OperatorDeclareNode,
    BlockNode, OperatorTable, Associativity, TernaryIfNode,
    ListNode, RangeNode, DoBlockNode
)


class ParseError(Exception):
    def __init__(self, message: str, token: Token = None):
        if token:
            message = f"{message} at line {token.line}, column {token.column}"
        super().__init__(message)
        self.token = token


class Parser:
    def __init__(self, tokens: List[Token], op_table: OperatorTable):
        self.tokens = tokens
        self.pos = 0
        self.op_table = op_table

    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def at_end(self) -> bool:
        return self.check(TokenType.EOF)

    def expect(self, token_type: TokenType, value: str = None) -> Token:
        token = self.current()
        if token.type != token_type:
            raise ParseError(f"Expected {token_type.name}, got {token_type.name} ('{token.value}')", token)
        if value is not None and token.value != value:
            raise ParseError(f"Expected '{value}', got '{token.value}'", token)
        return self.advance()

    def check(self, token_type: TokenType, value: str = None) -> bool:
        token = self.current()
        if token.type != token_type:
            return False
        return value is None or token.value == value

    def match(self, token_type: TokenType, value: str = None) -> bool:
        if self.check(token_type, value):
            self.advance()
            return True
        return False

    def _loc(self, token: Token = None):
        if token is None:
            token = self.current()
        return {'line': token.line, 'col': token.column}

    def parse_program(self) -> BlockNode:
        statements = []
        while not self.check(TokenType.EOF):
            statements.append(self.parse_statement())
        return BlockNode(statements)

    def parse_one_statement(self) -> Optional[ASTNode]:
        if self.at_end():
            return None
        stmt = self.parse_statement()
        return stmt

    def parse_statement(self) -> ASTNode:
        if self.check(TokenType.OP_DECLARE):
            return self.parse_operator_declare()
        if self.check(TokenType.FUN):
            return self.parse_function_def()
        if self.check(TokenType.IDENTIFIER) and self.peek(1).type == TokenType.ASSIGN:
            return self.parse_assignment()
        if self.check(TokenType.DO):
            return self.parse_do_block()
        return self.parse_expression()

    def parse_do_block(self) -> DoBlockNode:
        loc = self._loc()
        self.expect(TokenType.DO)
        stmts = []
        while not self.check(TokenType.END) and not self.at_end():
            stmts.append(self.parse_statement())
        self.expect(TokenType.END)
        return DoBlockNode(statements=stmts, **loc)

    def parse_operator_declare(self) -> OperatorDeclareNode:
        loc = self._loc()
        self.expect(TokenType.OP_DECLARE)
        op_token = self.current()
        if op_token.type == TokenType.OPERATOR:
            self.advance()
        elif op_token.type == TokenType.IDENTIFIER:
            self.advance()
        else:
            raise ParseError(f"Expected operator symbol, got {op_token.type.name}", op_token)
        self.expect(TokenType.COMMA)

        negative = False
        if self.check(TokenType.OPERATOR, '-'):
            negative = True
            self.advance()

        prec_token = self.expect(TokenType.NUMBER)
        precedence = int(float(prec_token.value))
        if negative:
            precedence = -precedence

        self.expect(TokenType.COMMA)

        assoc_token = self.current()
        if assoc_token.type == TokenType.LEFT_ASSOC:
            associativity = Associativity.LEFT
        elif assoc_token.type == TokenType.RIGHT_ASSOC:
            associativity = Associativity.RIGHT
        else:
            raise ParseError(f"Expected 'left' or 'right', got {assoc_token.value}", assoc_token)
        self.advance()

        left_param = None
        right_param = None
        body = None

        if self.check(TokenType.LPAREN):
            self.advance()
            left_param = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COMMA)
            right_param = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.RPAREN)
            self.expect(TokenType.ASSIGN)
            body = self.parse_expression()

        return OperatorDeclareNode(
            op_token.value, precedence, associativity,
            left_param, right_param, body, **loc
        )

    def parse_function_def(self) -> FunctionDefNode:
        loc = self._loc()
        self.expect(TokenType.FUN)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LPAREN)

        params = []
        if not self.check(TokenType.RPAREN):
            params.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                params.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.RPAREN)

        if self.check(TokenType.DO):
            body = self.parse_do_block()
        else:
            self.expect(TokenType.ASSIGN)
            body = self.parse_expression()

        return FunctionDefNode(name_token.value, params, body, **loc)

    def parse_assignment(self) -> AssignmentNode:
        loc = self._loc()
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        return AssignmentNode(name_token.value, value, **loc)

    def parse_expression(self, min_precedence: int = 0) -> ASTNode:
        left = self.parse_prefix()
        left.line = left.line or self.current().line
        left.col = left.col or self.current().column

        while True:
            token = self.current()

            if token.type == TokenType.QUESTION and 0 >= min_precedence:
                loc = self._loc()
                self.advance()
                then_expr = self.parse_expression(0)
                self.expect(TokenType.COLON)
                else_expr = self.parse_expression(0)
                left = TernaryIfNode(left, then_expr, else_expr, **loc)
                continue

            if token.type == TokenType.DOTDOT:
                loc = self._loc()
                self.advance()
                right = self.parse_prefix()
                left = RangeNode(left, right, **loc)
                continue

            is_operator_token = (
                token.type == TokenType.OPERATOR
                or (token.type == TokenType.IDENTIFIER and self.op_table.has_operator(token.value))
            )

            if is_operator_token:
                op_symbol = token.value
                if not self.op_table.has_operator(op_symbol):
                    raise ParseError(f"Unknown operator '{op_symbol}'", token)

                current_prec = self.op_table.get_precedence(op_symbol)
                if current_prec < min_precedence:
                    break

                associativity = self.op_table.get_associativity(op_symbol)
                if associativity == Associativity.LEFT:
                    next_min_prec = current_prec + 1
                else:
                    next_min_prec = current_prec

                loc = self._loc()
                self.advance()
                right = self.parse_expression(next_min_prec)
                left = BinaryOpNode(left, op_symbol, right, **loc)
            else:
                break

        return left

    def parse_prefix(self) -> ASTNode:
        token = self.current()

        if token.type == TokenType.NUMBER:
            self.advance()
            return NumberNode(float(token.value), line=token.line, col=token.column)

        if token.type == TokenType.IDENTIFIER:
            self.advance()
            if self.check(TokenType.LPAREN):
                return self.parse_function_call(token)
            return IdentifierNode(token.value, line=token.line, col=token.column)

        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if token.type == TokenType.LBRACKET:
            return self.parse_list()

        if token.type == TokenType.DO:
            return self.parse_do_block()

        if token.type == TokenType.OPERATOR:
            if token.value in ('+', '-', '!', '~'):
                self.advance()
                operand = self.parse_prefix()
                return UnaryOpNode(token.value, operand, line=token.line, col=token.column)
            raise ParseError(f"Unexpected prefix operator '{token.value}'", token)

        raise ParseError(f"Unexpected token '{token.value}' ({token.type.name})", token)

    def parse_function_call(self, name_token: Token) -> FunctionCallNode:
        loc = self._loc(name_token)
        self.expect(TokenType.LPAREN)
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())
        self.expect(TokenType.RPAREN)
        return FunctionCallNode(name_token.value, args, **loc)

    def parse_list(self) -> ListNode:
        loc = self._loc()
        self.expect(TokenType.LBRACKET)
        elements = []
        if not self.check(TokenType.RBRACKET):
            elements.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                elements.append(self.parse_expression())
        self.expect(TokenType.RBRACKET)
        return ListNode(elements=elements, **loc)
