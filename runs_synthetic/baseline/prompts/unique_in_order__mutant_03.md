You are an automated program repair system for introductory programming assignments.

## Assignment
Write a function with the exact signature `unique_in_order(lst)`. The argument `lst` is a list whose elements are ints and/or strings. Your function must return a NEW list containing the same elements in their original order, except that every run of consecutive equal elements is collapsed to a single copy.

Only adjacent duplicates are removed. If a value appears again later, after a different value has occurred in between, it must be kept again. This is the key difference from removing all duplicates: `[1, 1, 2, 1]` becomes `[1, 2, 1]`, not `[1, 2]`. Elements are compared with ordinary equality (`==`) and comparisons are case-sensitive for strings, so `"A"` and `"a"` are different values. Note that the int `1` and the string `"1"` are different values as well.

Precise edge-case semantics: an empty list returns an empty list `[]`; a one-element list returns a one-element list with that same element; a list where every element is equal returns a single-element list. The value `0` is a normal element and must be kept, so `[0, 0, 0]` returns `[0]`. Do not mutate the input list; build and return a fresh list, and do not sort anything.

Worked examples:
- `unique_in_order([1, 1, 2, 1])` returns `[1, 2, 1]`.
- `unique_in_order(["a", "a", "b", "b", "a"])` returns `["a", "b", "a"]`.
- `unique_in_order([])` returns `[]`.

A good strategy is to walk the list once and append an element only when it differs from the last element you appended.

The solution must be a Python function named `unique_in_order`.

## Visible test suite
assert unique_in_order([]) == []
assert unique_in_order([1]) == [1]
assert unique_in_order([1, 1]) == [1]
assert unique_in_order([1, 1, 2, 1]) == [1, 2, 1]
assert unique_in_order([1, 2, 3]) == [1, 2, 3]
assert unique_in_order([1, 1, 1, 1]) == [1]
assert unique_in_order(["a", "a", "b", "b", "a"]) == ["a", "b", "a"]
assert unique_in_order([1, "1", 1]) == [1, "1", 1]
assert unique_in_order([2, 2, 2, 3, 3, 1, 1, 2]) == [2, 3, 1, 2]
assert unique_in_order(["A", "a", "A"]) == ["A", "a", "A"]
assert unique_in_order([0, 0, 0]) == [0]
assert unique_in_order([5, 4, 4, 5, 5, 4]) == [5, 4, 5, 4]
assert unique_in_order(["x"]) == ["x"]
assert unique_in_order([1, 2, 2, 3, 3, 3, 4]) == [1, 2, 3, 4]

## Buggy student submission
```python
def unique_in_order(lst):
    return [lst[i] for i in range(len(lst)) if i == 0 or lst[i] != lst[i + 1]]

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
