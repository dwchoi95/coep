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

## Example repairs from past students of THIS assignment
### Example 1: buggy submission
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
### Example 1: corrected version
```python
def unique_day(date, possible_birthdays):
    count = 0
    for birthday in possible_birthdays:
        if birthday[1] == date:
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
        if birthday[0] == month:
            if unique_day(birthday[1], possible_birthdays):
                return True
    return False

```
### Example 2: buggy submission
```python
def count_dates(date, possible_birthdays):
    count = 0
    for i in possible_birthdays:
        if i[1] == date:
            count += 1
    return count
    
def unique_day(date, possible_birthdays):
    if count_dates(date, possible_birthdays) == 1:
        return True
    else:
        return False
    
def count_months(month, possible_birthdays):
    count = 0
    for i in possible_birthdays:
        if i[0] == month:
            count += 1
    return count
    
def unique_month(month, possible_birthdays):
    if count_months(month, possible_birthdays) == 1:
        return True
    else:
        return False


def contains_unique_day(month, possible_birthdays):
    days_in_month = ()
    for i in possible_birthdays:
        if i[0] == month:
            days_in_month += (i,)
    for x in days_in_month:
        if unique_day(x[1], possible_birthdays) == False:
            return True
        else:
            return False
           
                
        
    
    
    
   

```
### Example 2: corrected version
```python
def unique_day(day, possible_birthdays):
    counter = 0
    for i in possible_birthdays:
        if day == i[1]:
            counter += 1
    if counter == 1:
        return True
    else:
        return False

def unique_month(month, possible_birthdays):
    counter = 0
    for i in possible_birthdays:
        if month == i[0]:
            counter += 1
    if counter == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    unique = ()
    for i in possible_birthdays:
        if unique_day(i[1], possible_birthdays):
            unique += (i,)
    for i in unique:
        if month == i[0]:
            return True
    else:
        return False

```
### Example 3: buggy submission
```python
def count_dates(date, possible_birthdays):
    count = 0
    for i in possible_birthdays:
        if i[1] == date:
            count += 1
    return count

def unique_day(date, possible_birthdays):
    if count_dates(date, possible_birthdays) == 1:
        return True
    else:
        return False
    

def unique_month(month, possible_birthdays):
    return

def contains_unique_day(month, possible_birthdays):
    return 

```
### Example 3: corrected version
```python
def unique_day(day, possible_birthdays):
    counter = 0
    for j in possible_birthdays:
        if day == j[1]:
            counter += 1
    if counter != 1:
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    counter = 0
    for j in possible_birthdays:
        if month == j[0]:
            counter +=1
    if counter != 1:
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    for j in possible_birthdays:
        if month != j[0]:
            continue
        else:
            if unique_day(j[1],possible_birthdays):
                return True
    return False


```
### Example 4: buggy submission
```python
def unique_day(day, possible_birthdays):
    count=0
    for i in possible_birthdays:
        if i[1]==day:
            count+=1
    if count>1:
        check=False
    else:
        check=True
    return check

def unique_month(month, possible_birthdays):
    count=0
    for i in possible_birthdays:
        if i[0]==month:
            count+=1
    if count>1:
        check=False
    else:
        check=True
    return check


def contains_unique_day(month, possible_birthdays):
    birthdays=()
    for i in possible_birthdays:
        if i[0]==month:
            birthdays+=(i,)
    for j in birthdays:
        if unique_day(j[1], possible_birthdays):
            return True
    return False
            

```
### Example 4: corrected version
```python
def unique_day(date, possible_birthdays):
    if len(tuple(filter(lambda x: x[1] == date ,possible_birthdays))) == 1:
        return True
    else:
        return False
    

def unique_month(month, possible_birthdays):
    if len(tuple(filter(lambda x: x[0] == month ,possible_birthdays))) == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    birthdays = tuple(filter(lambda x: x[0] == month ,possible_birthdays))
    for i in birthdays:
        if unique_day(i[1], possible_birthdays) == True:
            return True
    else:
        return False 

```
### Example 5: buggy submission
```python
def unique_day(date, possible_birthdays):

    count =0

    for i in possible_birthdays:

        if date==i[1]:

            count+=1

    return count==1

def unique_month(month, possible_birthdays):

    count =0

    for i in possible_birthdays:

        if month==i[0]:

            count+=1

    return count==1

def contains_unique_day(month, possible_birthdays):

    daysinmonth=()

    count=0

    for i in possible_birthdays:

        if month==i[0]:

            daysinmonth+=(i[1],)

    for i in daysinmonth:

        if unique_day(i,possible_birthdays):
            count+=1

    return count==1

```
### Example 5: corrected version
```python
def unique_day(day, possible_birthdays):
       
    days = 0 
        
    for i in range(len(possible_birthdays)): #creating the for loop for the range of possible birthdays
        if possible_birthdays[i][1] == day: # looking for the date according to the list
            days = days + 1
            
    if days == 1:  #return when the day matches
        return True
    else:
        return False 
        


def unique_month(month, possible_birthdays):
    
    months = 0
    for j in range(len(possible_birthdays)):  #creating the for loop for the range of possible birthday months 
        
        if possible_birthdays[j][0] == month:# looking for the month according to the list
            months = months + 1
    if months == 1: #return when the month matches
        return True
    else:
        return False
        
def contains_unique_day(month, possible_birthdays):
    
    x = () 
    
    for k in range(len(possible_birthdays)):
        
        if possible_birthdays[k][0] == month:
            
            x = x + (possible_birthdays[k],)
            
    for l in range(len(x)):
        if unique_day(x[l][1], possible_birthdays):
            return True
    return False 

```

## Buggy student submission
```python
def unique_day(date, possible_birthdays):
    total= 0
    for i in possible_birthdays:
        if day == i[1]:
            total= total + 1
    return total == 1

def unique_month(month, possible_birthdays):
    return

def contains_unique_day(month, possible_birthdays):
    return 

```

## Observed failures when running the submission
- unique_day("1", [["January", "1"], ["February", "1"]]) expected false but got NameError: name 'day' is not defined
- unique_day("January", [["January", "1"], ["January", "2"]]) expected false but got null
- unique_day("January", [["January", "1"], ["February", "1"]]) expected true but got null
- unique_day("January", [["January", "1"], ["January", "2"]]) expected true but got null
- unique_day("January", [["January", "1"], ["February", "1"]]) expected false but got null

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
