from coep.repairlib import candidates_generic, first_passing, failing_tests
from coep.evaluate import rps
import ast

TESTS = [
    {"args": [[70, 80, 90]], "expected": [70, 90, 80.0]},
    {"args": [[100]], "expected": [100, 100, 100.0]},
    {"args": [[50.5, 60.5]], "expected": [50.5, 60.5, 55.5]},
    {"args": [[-10, 0, 10]], "expected": [-10, 10, 0.0]},
    {"args": [[1, 2]], "expected": [1, 2, 1.5]},
    {"args": [[1, 2, 3]], "expected": [1, 3, 2.0]},
    {"args": [[0, 0, 0]], "expected": [0, 0, 0.0]},
    {"args": [[59.9, 60.1, 60.0]], "expected": [59.9, 60.1, 60.0]},
    {"args": [[85, 92, 78, 95, 88]], "expected": [78, 95, 87.6]},
    {"args": [[1, 2, 4]], "expected": [1, 4, 2.33]},
    {"args": [[-5, -15, -10]], "expected": [-15, -5, -10.0]},
    {"args": [[2.675, 2.675]], "expected": [2.675, 2.675, 2.67]},
    {"args": [[0.1, 0.2, 0.3]], "expected": [0.1, 0.3, 0.2]},
    {"args": [[10, 20, 30, 40]], "expected": [10, 40, 25.0]},
]

class RoundWrapper(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
    
    def visit_Return(self, node):
        if isinstance(node.value, ast.List) and len(node.value.elts) >= 3:
            third = node.value.elts[2]
            if isinstance(third, ast.BinOp) and isinstance(third.op, ast.Div):
                rounded = ast.Call(
                    func=ast.Name(id='round', ctx=ast.Load()),
                    args=[third, ast.Constant(value=2)],
                    keywords=[]
                )
                node.value.elts[2] = rounded
                self.changed = True
                return node
        return self.generic_visit(node)

def _try_add_round(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    
    transformer = RoundWrapper()
    new_tree = transformer.visit(tree)
    
    if transformer.changed:
        try:
            new_source = ast.unparse(new_tree)
            return new_source
        except Exception:
            pass
    
    return None

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    try:
        result = failing_tests(source, "grade_stats", TESTS)
    except Exception:
        return None
    
    if not result.compiled:
        return None
    
    if result.passed == result.total:
        return source
    
    fixed = _try_add_round(source)
    if fixed is not None:
        try:
            result = failing_tests(fixed, "grade_stats", TESTS)
            if result.compiled and result.passed == result.total:
                if rps(source, fixed) <= 0.35:
                    return fixed
        except Exception:
            pass
    
    try:
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        repaired = first_passing(candidates, "grade_stats", TESTS, source, max_rps=0.35, max_checks=800)
        if repaired is not None:
            return repaired
    except Exception:
        pass
    
    try:
        candidates = candidates_generic(source, max_edits=2, budget=2000)
        repaired = first_passing(candidates, "grade_stats", TESTS, source, max_rps=0.35, max_checks=800)
        if repaired is not None:
            return repaired
    except Exception:
        pass
    
    return None
