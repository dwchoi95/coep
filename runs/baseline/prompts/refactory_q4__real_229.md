You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Sorting Tuples
Can we sort items other than integers? For this question, you will be sorting tuples! We represent a person using a tuple (<gender>, <age>). Given a list of people, write a function sort_age that sorts the people and return a list in an order such that the older people are at the front of the list. An example of the list of people is [("M", 23), ("F", 19), ("M", 30)]. The sorted list would look like [("M", 30), ("M", 23), ("F", 19)]. You may assume that no two members in the list of people are of the same age.

The solution must be a Python function named `sort_age`.

## Visible test suite
assert sort_age([["F", 19]]) == [["F", 19]]
assert sort_age([["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18]]
assert sort_age([["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19]]
assert sort_age([]) == []

## Buggy student submission
```python
def sort_age(lst):
    youngest = lst[0][1]
    for item in lst:
        if item[1] < youngest:
            youngest = item[1]
            lst.remove(item)
            lst = [item,] + lst
            
    return lst


```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
