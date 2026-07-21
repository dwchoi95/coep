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
def unique_day(date, possible_birthdays):
    for i in range(0,len(possible_birthdays)):
        list_final = [x for x in possible_birthdays[i][1]]
        list_final = sorted(list_final)
        if date == list_final[i] and date != list_final[i+1] and date != list_final[i-1]:
            return True
        else:
            return False
                
def unique_month(month, possible_birthdays):
    for i in range(0,len(possible_birthdays)):
        list = [x for x in possible_birthdays[i][0]]
        list = sorted(list)
        if month == list[i] and month != list[i+1] and month != list[i-1]:
            return True
        else:
            return False

def contains_unique_day(month, possible_birthdays):
    month_tuple = ()
    for i in range(0,len(possible_birthdays)):
        if possible_birthdays[i][0] == month:
            month_tuple = month_tuple + (possible_birthdays[i][1],)
    for x in month_tuple:
        for i in range(0,len(possible_birthdays)):
            if x == possible_birthdays[i][1]:
                return False
            else:
                return True
        

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
