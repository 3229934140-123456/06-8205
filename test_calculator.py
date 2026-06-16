import unittest
from calculator import CalculatorEngine
from calc_ast import Associativity


class TestCalculatorEngine(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_basic_arithmetic(self):
        self.assertEqual(self.calc.execute("2 + 3 * 4"), 14)
        self.assertEqual(self.calc.execute("(2 + 3) * 4"), 20)
        self.assertEqual(self.calc.execute("10 - 2 * 3 + 4"), 8)
        self.assertEqual(self.calc.execute("100 / 5 / 2"), 10)
        self.assertEqual(self.calc.execute("2 ** 3 ** 2"), 512)

    def test_unary_operators(self):
        self.assertEqual(self.calc.execute("-5"), -5)
        self.assertEqual(self.calc.execute("-(-5)"), 5)
        self.assertEqual(self.calc.execute("+5"), 5)
        self.assertEqual(self.calc.execute("!0"), 1)
        self.assertEqual(self.calc.execute("!1"), 0)

    def test_comparison_operators(self):
        self.assertEqual(self.calc.execute("5 < 10"), 1)
        self.assertEqual(self.calc.execute("5 > 10"), 0)
        self.assertEqual(self.calc.execute("5 == 5"), 1)
        self.assertEqual(self.calc.execute("5 != 5"), 0)
        self.assertEqual(self.calc.execute("5 <= 5"), 1)
        self.assertEqual(self.calc.execute("5 >= 10"), 0)

    def test_logical_operators(self):
        self.assertEqual(self.calc.execute("1 && 1"), 1)
        self.assertEqual(self.calc.execute("1 && 0"), 0)
        self.assertEqual(self.calc.execute("1 || 0"), 1)
        self.assertEqual(self.calc.execute("0 || 0"), 0)
        self.assertEqual(self.calc.execute("1 || 0 && 0"), 1)

    def test_ternary_conditional(self):
        self.assertEqual(self.calc.execute("1 ? 10 : 20"), 10)
        self.assertEqual(self.calc.execute("0 ? 10 : 20"), 20)
        self.assertEqual(self.calc.execute("5 > 3 ? 100 : 200"), 100)
        self.assertEqual(self.calc.execute("5 < 3 ? 100 : 200"), 200)

    def test_ternary_short_circuit(self):
        self.assertEqual(self.calc.execute("1 ? 42 : (10 / 0)"), 42)
        self.assertEqual(self.calc.execute("0 ? (10 / 0) : 99"), 99)

    def test_variable_assignment(self):
        self.calc.execute("x = 10")
        self.assertEqual(self.calc.execute("x"), 10)
        self.calc.execute("y = x * 2")
        self.assertEqual(self.calc.execute("y"), 20)
        self.calc.execute("x = x + 5")
        self.assertEqual(self.calc.execute("x"), 15)

    def test_builtin_functions(self):
        self.assertEqual(self.calc.execute("abs(-5)"), 5)
        self.assertEqual(self.calc.execute("sqrt(16)"), 4)
        self.assertEqual(self.calc.execute("pow(2, 3)"), 8)
        self.assertEqual(self.calc.execute("max(1, 5, 3)"), 5)
        self.assertEqual(self.calc.execute("min(1, 5, 3)"), 1)

    def test_function_definition_and_call(self):
        self.calc.execute("fun square(x) = x * x")
        self.assertEqual(self.calc.execute("square(5)"), 25)
        self.assertEqual(self.calc.execute("square(3) + square(4)"), 25)

    def test_user_defined_if_function(self):
        self.calc.execute("fun if(c, t, e) = c * t + (1 - c) * e")
        self.assertEqual(self.calc.execute("if(1, 10, 20)"), 10)
        self.assertEqual(self.calc.execute("if(0, 10, 20)"), 20)

    def test_function_with_multiple_params(self):
        self.calc.execute("fun add(a, b) = a + b")
        self.assertEqual(self.calc.execute("add(3, 4)"), 7)
        self.calc.execute("fun avg(a, b, c) = (a + b + c) / 3")
        self.assertEqual(self.calc.execute("avg(2, 4, 6)"), 4)

    def test_recursive_function_ternary(self):
        self.calc.execute("fun fact(n) = n == 0 ? 1 : n * fact(n - 1)")
        self.assertEqual(self.calc.execute("fact(5)"), 120)
        self.assertEqual(self.calc.execute("fact(0)"), 1)
        self.assertEqual(self.calc.execute("fact(3)"), 6)

    def test_recursive_fibonacci(self):
        self.calc.execute("fun fib(n) = n < 2 ? n : fib(n - 1) + fib(n - 2)")
        self.assertEqual(self.calc.execute("fib(0)"), 0)
        self.assertEqual(self.calc.execute("fib(1)"), 1)
        self.assertEqual(self.calc.execute("fib(5)"), 5)
        self.assertEqual(self.calc.execute("fib(10)"), 55)

    def test_operator_declaration_basic(self):
        self.calc.execute("op @@, 5, left")
        self.calc.define_operator_semantic('@@', lambda a, b: a + 2 * b)
        self.assertEqual(self.calc.execute("3 @@ 4"), 11)

    def test_operator_declaration_with_semantic_inline(self):
        self.calc.execute("op @@, 5, left (a, b) = a + 2 * b")
        self.assertEqual(self.calc.execute("3 @@ 4"), 3 + 2 * 4)
        self.assertEqual(self.calc.execute("10 @@ 5"), 10 + 2 * 5)

    def test_inline_operator_precedence_higher(self):
        self.calc.execute("op @@, 15, left (a, b) = a + b")
        self.assertEqual(self.calc.execute("2 * 3 @@ 4"), 2 * (3 + 4))
        self.assertEqual(self.calc.execute("2 @@ 3 * 4"), (2 + 3) * 4)

    def test_inline_operator_precedence_lower(self):
        self.calc.execute("op @@, 5, left (a, b) = a + b")
        self.assertEqual(self.calc.execute("2 + 3 @@ 4 * 5"), (2 + 3) + (4 * 5))

    def test_inline_operator_right_assoc(self):
        self.calc.execute("op ->, 8, right (a, b) = a ** b")
        self.assertEqual(self.calc.execute("2 -> 3 -> 2"), 2 ** (3 ** 2))

    def test_inline_operator_left_assoc(self):
        self.calc.execute("op ->, 8, left (a, b) = a ** b")
        self.assertEqual(self.calc.execute("2 -> 3 -> 2"), (2 ** 3) ** 2)

    def test_same_script_op_declare_and_use(self):
        program = """
op @@, 15, left (a, b) = a + b
2 @@ 3 * 4
"""
        self.assertEqual(self.calc.execute(program), (2 + 3) * 4)

    def test_same_script_multiple_op_declare(self):
        program = """
op ++, 11, left (a, b) = a + b
op --, 8, left (a, b) = a - b
2 ++ 3 -- 4 * 5
"""
        self.assertEqual(self.calc.execute(program), (2 + 3) - (4 * 5))

    def test_inline_operator_uses_closure_variables(self):
        program = """
base = 10
op +++, 5, left (a, b) = base * a + b
3 +++ 4
"""
        self.assertEqual(self.calc.execute(program), 10 * 3 + 4)

    def test_builtin_operator_override_prevented(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.calc.execute("op +, 20, left (a,b) = a - b")

    def test_unknown_operator(self):
        with self.assertRaises((SyntaxError, RuntimeError)):
            self.calc.execute("2 $$$ 3")

    def test_undefined_variable(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("undefined_var_xyz")

    def test_undefined_function(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("undefined_func_xyz(1, 2)")

    def test_function_arity_mismatch(self):
        self.calc.execute("fun add(a, b) = a + b")
        with self.assertRaises(RuntimeError):
            self.calc.execute("add(1)")
        with self.assertRaises(RuntimeError):
            self.calc.execute("add(1, 2, 3)")

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("10 / 0")

    def test_invalid_precedence(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.calc.execute("op $$$, -1, left")
        with self.assertRaises((ValueError, RuntimeError)):
            self.calc.execute("op $$$, 101, left")

    def test_parentheses_override_precedence(self):
        self.calc.execute("op @@, 5, left (a, b) = a + b")
        self.assertEqual(self.calc.execute("2 * (3 @@ 4)"), 2 * (3 + 4))
        self.assertEqual(self.calc.execute("(2 * 3) @@ 4"), (2 * 3) + 4)

    def test_function_closure(self):
        self.calc.execute("x = 10")
        self.calc.execute("fun addX(y) = x + y")
        self.calc.execute("x = 20")
        self.assertEqual(self.calc.execute("addX(5)"), 25)

    def test_operator_without_semantic(self):
        self.calc.execute("op $$$, 5, left")
        with self.assertRaises(RuntimeError):
            self.calc.execute("2 $$$ 3")

    def test_higher_precedence_builtin(self):
        self.calc.execute("op $$, 11, left (a, b) = a + b")
        self.assertEqual(self.calc.execute("2 $$ 3 * 4"), (2 + 3) * 4)
        self.assertEqual(self.calc.execute("2 * 3 $$ 4"), 2 * (3 + 4))

    def test_lower_precedence_builtin(self):
        self.calc.execute("op $$, 8, left (a, b) = a + b")
        self.assertEqual(self.calc.execute("2 + 3 $$ 4 * 5"), 2 + 3 + (4 * 5))

    def test_bitwise_operators(self):
        self.assertEqual(self.calc.execute("5 & 3"), 1)
        self.assertEqual(self.calc.execute("5 | 3"), 7)
        self.assertEqual(self.calc.execute("5 ^ 3"), 6)
        self.assertEqual(self.calc.execute("8 >> 1"), 4)
        self.assertEqual(self.calc.execute("1 << 3"), 8)

    def test_nested_function_calls(self):
        self.calc.execute("fun square(x) = x * x")
        self.calc.execute("fun cube(x) = x * square(x)")
        self.assertEqual(self.calc.execute("cube(3)"), 27)
        self.assertEqual(self.calc.execute("square(cube(2))"), 64)

    def test_program_with_multiple_statements(self):
        program = """
x = 5
y = 10
fun add(a, b) = a + b
add(x, y)
"""
        self.assertEqual(self.calc.execute(program), 15)

    def test_gcd_recursive(self):
        self.calc.execute("fun gcd(a, b) = b == 0 ? a : gcd(b, a % b)")
        self.assertEqual(self.calc.execute("gcd(48, 18)"), 6)
        self.assertEqual(self.calc.execute("gcd(7, 13)"), 1)
        self.assertEqual(self.calc.execute("gcd(100, 25)"), 25)

    def test_recursion_limit(self):
        self.calc.set_max_recursion(50)
        self.calc.execute("fun loop(n) = n == 0 ? 0 : loop(n - 1)")
        self.assertEqual(self.calc.execute("loop(10)"), 0)
        try:
            self.calc.execute("loop(1000000)")
            self.fail("Should have raised recursion error")
        except RuntimeError:
            pass

    def test_operator_semantic_uses_builtin_function(self):
        self.calc.execute("op MAX, 5, left (a, b) = max(a, b)")
        self.assertEqual(self.calc.execute("3 MAX 7"), 7)
        self.assertEqual(self.calc.execute("10 MAX 5 MAX 20"), 20)

    def test_error_reporting_contains_line_info(self):
        program = """
x = 1
y = 2
z = x $ y
"""
        try:
            self.calc.execute(program)
            self.fail("Should have raised error")
        except (SyntaxError, RuntimeError) as e:
            msg = str(e)
            self.assertIn("line", msg.lower())
            self.assertIn("column", msg.lower())
            self.assertIn("3", msg)

    def test_user_if_differs_from_ternary(self):
        self.calc.execute("fun if(c, t, e) = t + e")
        ternary_result = self.calc.execute("1 ? 10 : 20")
        user_if_result = self.calc.execute("if(1, 10, 20)")
        self.assertEqual(ternary_result, 10)
        self.assertEqual(user_if_result, 30)


def run_tests():
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
