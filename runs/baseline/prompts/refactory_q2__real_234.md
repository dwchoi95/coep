You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Unique dates and months
Implement unique_day, unique_month and contains_unique_day.

The solution must be a Python function named `unique_day`.

## Visible test suite
assert unique_day("1", [["January", "1"], ["February", "1"]]) == false
assert unique_month("January", [["January", "1"], ["January", "2"]]) == false
assert unique_month("January", [["January", "1"], ["February", "1"]]) == true
assert contains_unique_day("January", [["January", "1"], ["January", "2"]]) == true
assert contains_unique_day("January", [["January", "1"], ["February", "1"]]) == false
assert contains_unique_day("February", [["January", "10"], ["February", "1"], ["February", "10"]]) == true
assert unique_day("3", [["January", "1"], ["January", "2"]]) == false
assert unique_month("March", [["January", "1"], ["February", "1"]]) == false
assert unique_day("1", [["January", "1"], ["January", "2"]]) == true

## Buggy student submission
```python
def unique_day(day, possible_birthdays):
    result = ()
    for p in possible_birthdays:
        pd = p[1]
        if day == pd:
            result = result + (day,)
    if len(result) > 1:
        return False
    return True

def unique_month(month, possible_birthdays):
    result = ()
    for p in possible_birthdays:
        pm = p[0]
        if month == pm:
            result = result + (month,)
    if len(result) > 1:
        return False
    return True
    
    
def contains_unique_day(month, possible_birthdays):
    result = ()
    for p in possible_birthdays:
        if month == p[0]:
            result = result + (p,)
    for r in result:
        if unique_day(r[1], possible_birthdays) == True:
            return True
    return False

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
