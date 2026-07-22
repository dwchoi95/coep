```python
def unique_day(date, possible_birthdays):
    count=0
    for i in possible_birthdays: 
        if i[1]==date:
            count+=1
    if count!=1:
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    if sum(month in i for i in possible_birthdays)!=1:
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    if unique_month(month, possible_birthdays): 
        return False
    else: 
        return True 
```
