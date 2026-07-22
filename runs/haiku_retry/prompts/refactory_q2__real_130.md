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
    for i in possible_birthdays:
        if i[1] == day:
            counter = counter + 1
    if counter > 1:
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    counter = 0
    for i in possible_birthdays:
        if i[0] == month:
            counter = counter + 1
    if counter > 1:
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    x = ()
    for i in possible_birthdays:
        if i[0] == month:
            x = x + (i,)
    total = 0
    for i in x:
        total = total + unique_day(i[1], possible_birthdays)
    if total != 0:
        return True
    else:
        return False

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED)
Your previous repair passes the tests but changes 49% of the program's tokens, exceeding the 35% relative-patch-size limit. It rewrites too much of the student's approach:
```python
def unique_day(date, possible_birthdays):
    count = 0
    for birthday in possible_birthdays:
        if date == birthday[1]:
            count += 1
    return count == 1

def unique_month(month, possible_birthdays):
    count = 0
    for birthday in possible_birthdays:
        if month == birthday[0]:
            count += 1
    return count == 1
    
def contains_unique_day(month, possible_birthdays):
    singlemonthbirthday = ()
    for birthmonth in possible_birthdays:
        if month == birthmonth[0]:
            singlemonthbirthday += (birthmonth,)
    for birthday in singlemonthbirthday:
        if unique_day(birthday[1], possible_birthdays) == True:
            return True
    return False

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
