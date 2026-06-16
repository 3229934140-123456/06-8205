import unittest
from calculator import CalculatorEngine, is_input_incomplete
from calc_ast import Associativity


class TestCalculatorEngine(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_basic_arithmetic(self):
        self.assertEqual(self.calc.execute("2 + 3 * 4"), 14)
        self.assertEqual(self.calc.execute("(2 + 3) * 4"), 20)
        self.assertEqual(self.calc.execute("10 - 2 * 3 + 4"), 8)
        self.assertEqual(self.calc.execute("2 ** 3 ** 2"), 512)

    def test_unary_operators(self):
        self.assertEqual(self.calc.execute("-5"), -5)
        self.assertEqual(self.calc.execute("-(-5)"), 5)
        self.assertEqual(self.calc.execute("!0"), 1)
        self.assertEqual(self.calc.execute("!1"), 0)

    def test_comparison_operators(self):
        self.assertEqual(self.calc.execute("5 < 10"), 1)
        self.assertEqual(self.calc.execute("5 == 5"), 1)
        self.assertEqual(self.calc.execute("5 != 5"), 0)

    def test_logical_operators(self):
        self.assertEqual(self.calc.execute("1 && 1"), 1)
        self.assertEqual(self.calc.execute("1 && 0"), 0)
        self.assertEqual(self.calc.execute("1 || 0"), 1)

    def test_ternary_conditional(self):
        self.assertEqual(self.calc.execute("1 ? 10 : 20"), 10)
        self.assertEqual(self.calc.execute("0 ? 10 : 20"), 20)
        self.assertEqual(self.calc.execute("5 > 3 ? 100 : 200"), 100)

    def test_ternary_short_circuit(self):
        self.assertEqual(self.calc.execute("1 ? 42 : (10 / 0)"), 42)
        self.assertEqual(self.calc.execute("0 ? (10 / 0) : 99"), 99)

    def test_variable_assignment(self):
        self.calc.execute("x = 10")
        self.assertEqual(self.calc.execute("x"), 10)
        self.calc.execute("y = x * 2")
        self.assertEqual(self.calc.execute("y"), 20)

    def test_builtin_functions(self):
        self.assertEqual(self.calc.execute("abs(-5)"), 5)
        self.assertEqual(self.calc.execute("sqrt(16)"), 4)
        self.assertEqual(self.calc.execute("pow(2, 3)"), 8)

    def test_function_definition_and_call(self):
        self.calc.execute("fun square(x) = x * x")
        self.assertEqual(self.calc.execute("square(5)"), 25)

    def test_user_defined_if_function(self):
        self.calc.execute("fun if(c, t, e) = c * t + (1 - c) * e")
        self.assertEqual(self.calc.execute("if(1, 10, 20)"), 10)
        self.assertEqual(self.calc.execute("if(0, 10, 20)"), 20)

    def test_recursive_function_ternary(self):
        self.calc.execute("fun fact(n) = n == 0 ? 1 : n * fact(n - 1)")
        self.assertEqual(self.calc.execute("fact(5)"), 120)
        self.assertEqual(self.calc.execute("fact(0)"), 1)

    def test_recursive_fibonacci(self):
        self.calc.execute("fun fib(n) = n < 2 ? n : fib(n - 1) + fib(n - 2)")
        self.assertEqual(self.calc.execute("fib(5)"), 5)
        self.assertEqual(self.calc.execute("fib(10)"), 55)

    def test_inline_operator_with_semantic(self):
        self.calc.execute("op @@, 5, left (a, b) = a + 2 * b")
        self.assertEqual(self.calc.execute("3 @@ 4"), 3 + 2 * 4)

    def test_same_script_op_declare_and_use(self):
        self.calc.execute("op @@, 15, left (a, b) = a + b\n2 @@ 3 * 4")
        self.assertEqual(self.calc.execute("2 @@ 3 * 4"), (2 + 3) * 4)

    def test_builtin_operator_override_prevented(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.calc.execute("op +, 20, left (a,b) = a - b")

    def test_unknown_operator(self):
        with self.assertRaises((SyntaxError, RuntimeError)):
            self.calc.execute("2 $ 3")

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("10 / 0")

    def test_gcd_recursive(self):
        self.calc.execute("fun gcd(a, b) = b == 0 ? a : gcd(b, a % b)")
        self.assertEqual(self.calc.execute("gcd(48, 18)"), 6)

    def test_recursion_limit(self):
        self.calc.set_max_recursion(50)
        self.calc.execute("fun loop(n) = n == 0 ? 0 : loop(n - 1)")
        self.assertEqual(self.calc.execute("loop(10)"), 0)
        with self.assertRaises(RuntimeError):
            self.calc.execute("loop(1000000)")


class TestDoBlock(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_simple_do_block(self):
        result = self.calc.execute("do\n  1 + 2\nend")
        self.assertEqual(result, 3)

    def test_do_block_with_local_vars(self):
        program = """do
  a = 10
  b = 20
  a + b
end"""
        self.assertEqual(self.calc.execute(program), 30)

    def test_do_block_local_scope(self):
        self.calc.execute("x = 100")
        program = """do
  x = 999
  x
end"""
        self.assertEqual(self.calc.execute(program), 999)
        self.assertEqual(self.calc.execute("x"), 100)

    def test_do_block_nested(self):
        program = """do
  a = 1
  do
    b = 2
    a + b
  end
end"""
        self.assertEqual(self.calc.execute(program), 3)

    def test_function_with_do_block_body(self):
        program = """fun area(w, h) do
  result = w * h
  result
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("area(3, 4)"), 12)

    def test_recursive_function_with_do_block(self):
        program = """fun fact(n) do
  n == 0 ? 1 : n * fact(n - 1)
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("fact(6)"), 720)

    def test_function_do_block_multiple_steps(self):
        program = """fun sum_squares(a, b) do
  sa = a * a
  sb = b * b
  sa + sb
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("sum_squares(3, 4)"), 25)

    def test_do_block_access_outer_scope(self):
        self.calc.execute("x = 10")
        self.assertEqual(self.calc.execute("do\n  x * 2\nend"), 20)


class TestListAndRange(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_list_literal(self):
        result = self.calc.execute("[1, 2, 3]")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_empty_list(self):
        result = self.calc.execute("[]")
        self.assertEqual(result, [])

    def test_list_with_expressions(self):
        result = self.calc.execute("[1 + 1, 2 * 3, 10 / 2]")
        self.assertEqual(result, [2.0, 6.0, 5.0])

    def test_range_syntax(self):
        result = self.calc.execute("1..5")
        self.assertEqual(result, [1, 2, 3, 4])

    def test_range_in_list_context(self):
        result = self.calc.execute("1..4")
        self.assertEqual(result, [1, 2, 3])

    def test_len_builtin(self):
        self.assertEqual(self.calc.execute("len([10, 20, 30])"), 3)

    def test_sum_builtin(self):
        self.assertEqual(self.calc.execute("sum([1, 2, 3, 4])"), 10)

    def test_max_min_on_list(self):
        self.assertEqual(self.calc.execute("max([5, 3, 8, 1])"), 8)
        self.assertEqual(self.calc.execute("min([5, 3, 8, 1])"), 1)

    def test_map_builtin(self):
        self.calc.execute("fun double(x) = x * 2")
        result = self.calc.execute("map(double, [1, 2, 3])")
        self.assertEqual(result, [2.0, 4.0, 6.0])

    def test_filter_builtin(self):
        self.calc.execute("fun isEven(x) = x % 2 == 0")
        result = self.calc.execute("filter(isEven, [1, 2, 3, 4, 5, 6])")
        self.assertEqual(result, [2.0, 4.0, 6.0])

    def test_list_concatenation(self):
        result = self.calc.execute("[1, 2] + [3, 4]")
        self.assertEqual(result, [1.0, 2.0, 3.0, 4.0])

    def test_push_builtin(self):
        result = self.calc.execute("push([1, 2], 3)")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_head_tail(self):
        self.assertEqual(self.calc.execute("head([10, 20, 30])"), 10)
        self.assertEqual(self.calc.execute("tail([10, 20, 30])"), [20.0, 30.0])

    def test_nth_builtin(self):
        self.assertEqual(self.calc.execute("nth([10, 20, 30], 1)"), 20)

    def test_range_function_builtin(self):
        result = self.calc.execute("range(5)")
        self.assertEqual(result, [0, 1, 2, 3, 4])
        result = self.calc.execute("range(2, 5)")
        self.assertEqual(result, [2, 3, 4])

    def test_sum_of_range(self):
        self.assertEqual(self.calc.execute("sum(1..6)"), 15)

    def test_type_builtin(self):
        self.assertEqual(self.calc.execute("type(42)"), "number")
        self.assertEqual(self.calc.execute("type([1,2])"), "list")

    def test_list_assigned_to_variable(self):
        self.calc.execute("xs = [10, 20, 30]")
        self.assertEqual(self.calc.execute("sum(xs)"), 60)
        self.assertEqual(self.calc.execute("len(xs)"), 3)

    def test_map_with_inline_function(self):
        self.calc.execute("fun square(x) = x * x")
        result = self.calc.execute("map(square, 1..5)")
        self.assertEqual(result, [1.0, 4.0, 9.0, 16.0])

    def test_filter_with_range(self):
        self.calc.execute("fun big(x) = x > 3")
        result = self.calc.execute("filter(big, 1..7)")
        self.assertEqual(result, [4, 5, 6])

    def test_head_empty_list_error(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("head([])")

    def test_nth_out_of_range_error(self):
        with self.assertRaises(RuntimeError):
            self.calc.execute("nth([1,2], 5)")


class TestErrorReporting(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_error_has_line_and_col(self):
        program = "x = 1\ny = x $ 2\nz = 3"
        try:
            self.calc.execute(program)
            self.fail("Should have raised")
        except (SyntaxError, RuntimeError) as e:
            msg = str(e)
            self.assertIn("line", msg.lower())

    def test_div_zero_error_points_to_source(self):
        try:
            self.calc.execute("10 / 0")
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("ZeroDivisionError", msg)

    def test_arity_error_in_function(self):
        self.calc.execute("fun f(a) = a + 1")
        try:
            self.calc.execute("f(1, 2)")
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("ArityError", msg)

    def test_recursion_error_shows_call_chain(self):
        self.calc.set_max_recursion(10)
        self.calc.execute("fun r(n) = r(n + 1)")
        try:
            self.calc.execute("r(0)")
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("RecursionError", msg)

    def test_multiline_error_points_to_correct_line(self):
        program = """fun add(a, b) = a + b
x = 10
y = add(1, 2, 3)"""
        try:
            self.calc.execute(program)
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("3", msg)


class TestReplMultiline(unittest.TestCase):
    def test_incomplete_do(self):
        self.assertTrue(is_input_incomplete("do\n  x = 1"))

    def test_complete_do(self):
        self.assertFalse(is_input_incomplete("do\n  x = 1\nend"))

    def test_incomplete_bracket(self):
        self.assertTrue(is_input_incomplete("[1, 2"))

    def test_complete_bracket(self):
        self.assertFalse(is_input_incomplete("[1, 2]"))

    def test_incomplete_paren(self):
        self.assertTrue(is_input_incomplete("fun f(a, b"))

    def test_complete_expression(self):
        self.assertFalse(is_input_incomplete("1 + 2"))

    def test_incomplete_fun_no_body(self):
        self.assertTrue(is_input_incomplete("fun f(a, b)"))

    def test_complete_fun_with_equals(self):
        self.assertFalse(is_input_incomplete("fun f(a, b) = a + b"))

    def test_complete_fun_with_do(self):
        self.assertFalse(is_input_incomplete("fun f(a) do\n  a\nend"))


class TestComments(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_line_comment(self):
        self.assertEqual(self.calc.execute("1 + 2 # this is a comment"), 3)

    def test_comment_only_line(self):
        result = self.calc.execute("# just a comment\n42")
        self.assertEqual(result, 42)


class TestListIndexing(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_list_index_basic(self):
        self.calc.execute("xs = [10, 20, 30, 40]")
        self.assertEqual(self.calc.execute("xs[0]"), 10)
        self.assertEqual(self.calc.execute("xs[2]"), 30)

    def test_list_index_error(self):
        self.calc.execute("xs = [1, 2, 3]")
        with self.assertRaises(RuntimeError):
            self.calc.execute("xs[10]")

    def test_list_slice_start_end(self):
        self.calc.execute("xs = [10, 20, 30, 40, 50]")
        result = self.calc.execute("xs[1:4]")
        self.assertEqual(result, [20.0, 30.0, 40.0])

    def test_list_slice_start_only(self):
        self.calc.execute("xs = [10, 20, 30, 40]")
        result = self.calc.execute("xs[1:]")
        self.assertEqual(result, [20.0, 30.0, 40.0])

    def test_list_slice_end_only(self):
        self.calc.execute("xs = [10, 20, 30, 40]")
        result = self.calc.execute("xs[:3]")
        self.assertEqual(result, [10.0, 20.0, 30.0])

    def test_list_index_after_map(self):
        self.calc.execute("fun double(x) = x * 2")
        result = self.calc.execute("map(double, [1, 2, 3])[1]")
        self.assertEqual(result, 4.0)

    def test_range_index(self):
        self.assertEqual(self.calc.execute("(1..10)[2]"), 3)


class TestControlFlow(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_if_do_end_simple(self):
        program = """if 1 do
  100
end"""
        self.assertEqual(self.calc.execute(program), 100)

    def test_if_do_end_false(self):
        program = """if 0 do
  100
end"""
        self.assertIsNone(self.calc.execute(program))

    def test_if_do_else_do(self):
        program = """if 0 do
  100
else do
  200
end"""
        self.assertEqual(self.calc.execute(program), 200)

    def test_if_do_else_expr(self):
        program = """if 0 do
  100
else 200
end"""
        self.assertEqual(self.calc.execute(program), 200)

    def test_if_with_multiple_statements(self):
        program = """if 1 do
  a = 10
  b = 20
  a + b
end"""
        self.assertEqual(self.calc.execute(program), 30)

    def test_while_do_end(self):
        self.calc.execute("i = 0")
        self.calc.execute("sum = 0")
        program = """while i < 5 do
  sum = sum + i
  i = i + 1
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("sum"), 10)
        self.assertEqual(self.calc.execute("i"), 5)

    def test_while_false(self):
        result = self.calc.execute("while 0 do 42 end")
        self.assertIsNone(result)

    def test_user_defined_if_function_still_works(self):
        self.calc.execute("fun if(c, t, e) = c * t + (1 - c) * e")
        self.assertEqual(self.calc.execute("if(1, 10, 20)"), 10)
        self.assertEqual(self.calc.execute("if(0, 10, 20)"), 20)

    def test_if_block_and_if_function_coexist(self):
        self.calc.execute("fun if(c, t, e) = c * t + (1 - c) * e")
        self.assertEqual(self.calc.execute("if(1, 10, 20)"), 10)
        program = """if 1 do
  100
end"""
        self.assertEqual(self.calc.execute(program), 100)


class TestForLoop(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_for_simple(self):
        program = """for x in [1, 2, 3] do
  x * 2
end"""
        result = self.calc.execute(program)
        self.assertEqual(result, 6.0)

    def test_for_with_accumulator(self):
        program = """for x, acc = 0 in [1, 2, 3, 4, 5] do
  acc = acc + x
end"""
        self.assertEqual(self.calc.execute(program), 15)

    def test_for_with_accumulator_product(self):
        program = """for x, acc = 1 in [1, 2, 3, 4, 5] do
  acc = acc * x
end"""
        self.assertEqual(self.calc.execute(program), 120)

    def test_for_with_range(self):
        program = """for x, acc = 0 in 1..11 do
  acc = acc + x
end"""
        self.assertEqual(self.calc.execute(program), 55)

    def test_for_with_filter(self):
        self.calc.execute("fun isEven(x) = x % 2 == 0")
        program = """for x, acc = 0 in 1..11 do
  if isEven(x) do
    acc = acc + x
  end
end"""
        self.assertEqual(self.calc.execute(program), 30)

    def test_for_variable_not_leaking(self):
        self.calc.execute("x = 999")
        self.calc.execute("for x in [1, 2, 3] do x end")
        self.assertEqual(self.calc.execute("x"), 999)


class TestScopeFix(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()

    def test_function_body_local_variable_not_leaking(self):
        program = """fun process(a, b) do
  temp = a * 2
  temp + b
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("process(3, 4)"), 10)
        with self.assertRaises(RuntimeError):
            self.calc.execute("temp")

    def test_nested_blocks_shadowing(self):
        self.calc.execute("x = 100")
        program = """do
  x = 200
  do
    x = 300
    x
  end
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("x"), 100)

    def test_function_with_same_name_as_outer(self):
        self.calc.execute("x = 5")
        program = """fun double(x) do
  x = x * 2
  x
end"""
        self.calc.execute(program)
        self.assertEqual(self.calc.execute("double(10)"), 20)
        self.assertEqual(self.calc.execute("x"), 5)


class TestRecursionErrorLocation(unittest.TestCase):
    def setUp(self):
        self.calc = CalculatorEngine()
        self.calc.set_max_recursion(10)

    def test_recursion_error_points_to_call_site(self):
        program = """fun loop(n) do
  loop(n + 1)
end

result = loop(0)
"""
        try:
            self.calc.execute(program)
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("RecursionError", msg)
            self.assertIn("line 2", msg)
            self.assertIn("column 3", msg)
            self.assertIn("Call stack", msg)
            self.assertIn("loop at line 2", msg)

    def test_mutual_recursion_error(self):
        program = """fun even(n) do
  n == 0 ? 1 : odd(n - 1)
end

fun odd(n) do
  n == 0 ? 0 : even(n - 1)
end

even(1000000)
"""
        try:
            self.calc.execute(program)
            self.fail("Should have raised")
        except RuntimeError as e:
            msg = str(e)
            self.assertIn("RecursionError", msg)
            self.assertIn("even at line", msg)
            self.assertIn("odd at line", msg)


class TestReplMultilineNew(unittest.TestCase):
    def test_incomplete_if(self):
        self.assertTrue(is_input_incomplete("if x > 0 do"))
        self.assertFalse(is_input_incomplete("if x > 0 do\n  1\nend"))

    def test_incomplete_while(self):
        self.assertTrue(is_input_incomplete("while i < 10 do"))
        self.assertFalse(is_input_incomplete("while i < 10 do\n  i = i + 1\nend"))

    def test_incomplete_for(self):
        self.assertTrue(is_input_incomplete("for x in [1,2] do"))
        self.assertTrue(is_input_incomplete("for x, acc = 0 in"))
        self.assertFalse(is_input_incomplete("for x in [1,2] do\n  x\nend"))


class TestDataProcessingScript(unittest.TestCase):
    def test_full_data_processing_pipeline(self):
        program = """# 数据处理脚本
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# 筛选偶数
fun isEven(x) = x % 2 == 0
evens = filter(isEven, data)

# 平方变换
fun square(x) = x * x
squared = map(square, evens)

# 求和
total = for x, acc = 0 in squared do
  acc = acc + x
end

# 求平均
avg = total / len(evens)
avg
"""
        calc = CalculatorEngine()
        result = calc.execute(program)
        evens = [2, 4, 6, 8, 10]
        expected = sum(x*x for x in evens) / len(evens)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)
