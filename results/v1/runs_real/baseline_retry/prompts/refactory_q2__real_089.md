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
    counter = 0
    for dates in possible_birthdays:
        if day == dates[1]:
            possible_birthdays = possible_birthdays[1:]
            counter = counter + 1 
    if counter == 1:
        return True
    else:
        return False 
    return

def unique_month(month, possible_birthdays):
    return

def contains_unique_day(month, possible_birthdays):
    return 

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED: rewrites too much)
Your previous repair passes the tests but changes 91% of the program's tokens, exceeding the 35% relative-patch-size limit. It discards the student's own approach:
```python
def unique_day(day, possible_birthdays):
    counter = 0
    for dates in possible_birthdays:
        if day == dates[1]:
            counter = counter + 1 
    if counter == 1:
        return True
    else:
        return False 
    return

def unique_month(month, possible_birthdays):
    counter = 0
    for dates in possible_birthdays:
        if month == dates[0]:
            counter = counter + 1
    if counter == 1:
        return True
    else:
        return False
    return

def contains_unique_day(month, possible_birthdays):
    for dates in possible_birthdays:
        if month == dates[0]:
            if unique_day(dates[1], possible_birthdays):
                return True
    return False

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens). Preserve the student's identifiers, structure, and approach exactly wherever they are not wrong.
Output ONLY the complete corrected program in a single ```python code block, nothing else.
