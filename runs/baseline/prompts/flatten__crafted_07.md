You are an automated program repair system for introductory programming assignments.

## Assignment
Write a function with the exact signature `def flatten(nested):` that takes a list `nested` whose elements are either integers or lists that themselves contain integers or further nested lists, to any depth. The function must return a new flat list containing every integer that appears anywhere inside `nested`, in left-to-right order, exactly as the integers would be encountered when reading the structure from left to right at every level.

Edge-case semantics you must get right: an empty input list produces an empty result, so `flatten([]) == []`. Empty sublists contribute nothing but must not cause errors; for example `flatten([1, [], 2]) == [1, 2]`. Nesting can be arbitrarily deep, so a value wrapped in many layers of lists, such as `[[[[1]]]]`, still yields just `[1]`. The integers themselves may be zero or negative and must be preserved exactly. Do not mutate the input list, do not sort the result, and do not remove duplicates -- every integer occurrence must appear in the output exactly once per occurrence, in order.

Worked examples:
- `flatten([1, [2, 3]])` returns `[1, 2, 3]`.
- `flatten([[1, 2], [3, [4]], 5])` returns `[1, 2, 3, 4, 5]`.
- `flatten([[[[1]]]])` returns `[1]`.

You may solve this with recursion, an explicit stack, or repeated single-level flattening passes; use `isinstance(item, list)` to decide whether an element needs further flattening. Only the standard library is allowed.

The solution must be a Python function named `flatten`.

## Visible test suite
assert flatten([]) == []
assert flatten([1, 2, 3]) == [1, 2, 3]
assert flatten([1, [2, 3]]) == [1, 2, 3]
assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
assert flatten([[[[1]]]]) == [1]
assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]
assert flatten([[], [], []]) == []
assert flatten([0]) == [0]
assert flatten([1, [], 2]) == [1, 2]
assert flatten([[1], [2], 3, [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]
assert flatten([-1, [-2, [-3]]]) == [-1, -2, -3]
assert flatten([[[]], [[[]]], 5]) == [5]
assert flatten([10, [20], [30, [40]], 50]) == [10, 20, 30, 40, 50]
assert flatten([[1, [2]], 3]) == [1, 2, 3]

## Buggy student submission
```python
def flatten(nested, result=[]):
    for item in nested:
        if isinstance(item, list):
            flatten(item, result)
        else:
            result.append(item)
    return result

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
