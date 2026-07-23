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
    list1 = []
    i = 0
    smallest = lst[0][1]
    s = lst[0]
    for i in range(1,len(lst)):
        if lst[i][1] < smallest:
            smallest = lst[i][1]
            s = lst[i]
    list1 += s
    return list1

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED)
Your previous repair does not pass all of the visible tests:
```python
def sort_age(lst):
    list1 = []
    i = 0
    while len(lst) > 0:
        smallest = lst[0][1]
        s = lst[0]
        for i in range(1,len(lst)):
            if lst[i][1] < smallest:
                smallest = lst[i][1]
                s = lst[i]
        list1.append(s)
        lst.remove(s)
    return list1

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
