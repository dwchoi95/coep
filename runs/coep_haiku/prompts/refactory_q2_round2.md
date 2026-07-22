You previously wrote the following per-assignment repair module for the assignment "refactory_q2":

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import ast

TESTS = [
    {"function": "unique_day", "args": ["1", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "unique_month", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": False},
    {"function": "unique_month", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": True},
    {"function": "contains_unique_day", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": True},
    {"function": "contains_unique_day", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "contains_unique_day", "args": ["February", [["January", "10"], ["February", "1"], ["February", "10"]]], "expected": True},
    {"function": "unique_day", "args": ["3", [["January", "1"], ["January", "2"]]], "expected": False},
    {"function": "unique_month", "args": ["March", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "unique_day", "args": ["1", [["January", "1"], ["January", "2"]]], "expected": True},
]

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Try candidates: first the original, then generated candidates
    def original_candidate():
        yield source
    
    candidates = chain(original_candidate(), candidates_generic(source, max_edits=1, budget=2000))
    
    # Use first_passing to find a valid repair
    repair_result = first_passing(candidates, "unique_day", TESTS, source, max_rps=0.35, max_checks=800)
    
    return repair_result

```

Evaluated on the sample buggy submissions, the outcomes were:
- real_007.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_293.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_359.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_386.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_431.py: NOT REPAIRED — TypeError: 'function' object is not iterable

For reference, the submissions the module failed on:

### Failed submission real_007.py
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

### Failed submission real_293.py
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

### Failed submission real_359.py
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

### Failed submission real_386.py
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

### Failed submission real_431.py
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

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
