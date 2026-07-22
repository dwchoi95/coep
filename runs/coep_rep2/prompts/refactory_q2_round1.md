You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Task: Unique dates and months
Implement unique_day, unique_month and contains_unique_day.

The solution must be a Python function named `unique_day`.

## Visible test suite (the repairer validates candidates against exactly these)
assert unique_day("1", [["January", "1"], ["February", "1"]]) == false
assert unique_month("January", [["January", "1"], ["January", "2"]]) == false
assert unique_month("January", [["January", "1"], ["February", "1"]]) == true
assert contains_unique_day("January", [["January", "1"], ["January", "2"]]) == true
assert contains_unique_day("January", [["January", "1"], ["February", "1"]]) == false
assert contains_unique_day("February", [["January", "10"], ["February", "1"], ["February", "10"]]) == true
assert unique_day("3", [["January", "1"], ["January", "2"]]) == false
assert unique_month("March", [["January", "1"], ["February", "1"]]) == false
assert unique_day("1", [["January", "1"], ["January", "2"]]) == true

### Reference solution 1
```python
def unique_day(day, possible_birthdays):
    count = 0
    for birthday in possible_birthdays:
        if birthday[1] == day:
            count += 1
    return count == 1

def unique_month(month, possible_birthdays):
    count = 0
    for birthday in possible_birthdays:
        if birthday[0] == month:
            count += 1
    return count == 1

def contains_unique_day(month, possible_birthdays):
    for birthday in possible_birthdays:
        if birthday[0] == month and unique_day(birthday[1], possible_birthdays):
            return True
    return False

```

### Reference solution 2
```python
def unique_day(day, possible_birthdays):

    count = 0

    for i in possible_birthdays:
        if day in i:
            count += 1
            
    if count == 1:
        return True
    else:
        return False
        
        
def unique_month(month, possible_birthdays):
    
    count = 0

    for i in possible_birthdays:
        if month in i:
            count += 1
            
    if count == 1:
        return True
    else:
        return False
        
def contains_unique_day(month, possible_birthdays):

    for i in possible_birthdays:
        if month in i:
            if unique_day(i[1],possible_birthdays):
                return True
                           
        else:
            continue

    return False
        

```

### Reference solution 3
```python
def unique_day(day, possible_birthdays):
    unique = ()
    for birthday in possible_birthdays:
        if day == birthday[1]:
            unique = unique + (day,)
    if len(unique) == 1:        
        return True
    return False

def unique_month(month, possible_birthdays):
    unique = ()
    for birthday in possible_birthdays:
        if month == birthday[0]:
            unique = unique + (month,)
    if len(unique) == 1:
        return True
    return False

def contains_unique_day(month, possible_birthdays):
    correct_months = ()
    for birthday in possible_birthdays:
        if unique_day(birthday[1], possible_birthdays):
            correct_months = correct_months + (birthday[0],)
    if month in correct_months:
        return True
    return False 

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: real_007.py)
```python
def unique_day(date, possible_birthdays):
       
    days = 0 
        
    for i in range(len(possible_birthdays)):
        if possible_birthdays[i][1] == days:
            day = day + 1
            
    if days == 1:
        return True
    else:
        return False 

def unique_month(month, possible_birthdays):
    
    month = 0
    
    for i in range(len(possible_birthdays)):
        if possible_birthdays[i][0] == month:
            day = day + 1
            
    if days == 1:
        return True
    else:
        return False 
        
def contains_unique_day(month, possible_birthdays):
    
    x = () 
    
    for i in range(len(possible_birthdays)):
        
        if possible_birthdays[i][0] == month:
            
            x = x + (possible_birthdays[i],)
    for j in range(len(x)):
        if unique_day(x[j][1], possible_birthdays):
            return True
        else:
            continue
    return False 

```
### Example buggy submission 2 (id: real_293.py)
```python
def unique_day(day, possible_birthdays):
    bdaylist = possible_birthdays
    count = 0
    while len(bdaylist) > 0:
        single = bdaylist[0]
        if single[1] == day:
            count = count + 1
        if count == 2:
            return False
            break
        bdaylist = bdaylist[1:]
    return True

def unique_month(month, possible_birthdays):
    bdaylist = possible_birthdays
    count = 0
    while len(bdaylist) > 0:
        single = bdaylist[0]
        if single[0] == month:
            count = count + 1
        if count == 2:
            return False
            break
        bdaylist = bdaylist[1:]
    return True

def contains_unique_day(month, possible_birthdays):
    month_list = ()
    bday_list = possible_birthdays
    while len(bday_list)>0:
        if bday_list[0][0]==month:
            month_list = month_list + (bday_list[0],)
        bday_list = bday_list[1:]
    
    while len(month_list)>0:
        if unique_day(month_list[0][1],possible_birthdays):
            return True
        month_list = month_list[1:]
    return False


```
### Example buggy submission 3 (id: real_359.py)
```python
def unique_day(day, possible_birthdays):
    bag = ()
    for date in possible_birthdays:
        if date[1] == day:
            bag += (date[1],)
    if len(bag) >= 2:
        return False
    return True

def unique_month(month, possible_birthdays):
    bag = ()
    for date in possible_birthdays:
        if date[0] == month:
            bag += (date[0],)
    if len(bag) >= 2:
        return False
    return True

def contains_unique_day(month, possible_birthdays):
    for date in possible_birthdays:
        if date[0] == month:
            day = date[1]
            if unique_day(day, possible_birthdays):
                return True
            else:
                continue
    return False

```
### Example buggy submission 4 (id: real_386.py)
```python
def unique_day(day, possible_birthdays):
    count = ()
    for i in range (len(possible_birthdays)):
        if day == possible_birthdays[i][1]:
            count = count + (possible_birthdays[i][1],)
    if len(count) < 2:
        return True
    else:
        return False

def unique_month(month, possible_birthdays):
    count = ()
    for i in range (len(possible_birthdays)):
        if month == possible_birthdays[i][0]:
            count = count + (possible_birthdays[i][0],)
    if len(count) < 2:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    return 

```
### Example buggy submission 5 (id: real_431.py)
```python
def unique_day(date, possible_birthdays):
    counter = 0
    for i in possible_birthdays:
        if i[1] == date:
            counter += 1
    if counter > 1:
        return False
    return True

def unique_month(month, possible_birthdays):
    counter = 0
    for i in possible_birthdays:
        if i[0] == month:
            counter += 1
    if counter > 1:
        return False
    return True

def contains_unique_day(month, possible_birthdays):
    new_tuple = ()
    for i in possible_birthdays:
        if i[0] == month:
            new_tuple += (i,)
        if len(new_tuple)>1:
            return False
        else:
            return unique_day(new_tupl[0][1], possible_birthdays)

```

## Helper library
You may use the helper library `coep.repairlib` (importable as shown):

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
```

- `candidates_generic(source, max_edits=1, budget=2000)` -> iterator of candidate
  programs obtained by small semantic edits at every applicable AST site
  (comparison/arithmetic/boolean operator swaps, integer off-by-one,
  boolean-constant flips, index shifts, argument swaps). `max_edits=2`
  enumerates pairs of edits (much larger; use a budget).
- `first_passing(candidates, entry, tests, original, max_rps=0.35, max_checks=800)`
  -> the first candidate passing ALL tests whose relative patch size vs the
  original is <= max_rps, else None. Each test is {"args": [...], "expected": ...}.
- `failing_tests(source, entry, tests)` -> RunResult with `.compiled`,
  `.passed`, `.total`, `.failures` (list of {index, args, expected, got, error}),
  useful for dispatching on the observed failure pattern.
- `rps(buggy, patched)` -> token-level relative patch size.
- `chain(gen1, gen2, ...)` -> compose candidate generators in priority order.
- Standard library (`ast`, `re`, `itertools`, ...) is fully available.


## Your task
Write a Python module that defines:

```python
def repair(source: str) -> str | None:
    ...
```

`repair` takes a buggy submission (a string containing a definition of `unique_day`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
