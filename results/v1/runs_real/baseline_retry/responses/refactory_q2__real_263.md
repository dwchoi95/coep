```python
def unique_day(date, possible_birthdays):
    if sum(date in b for b in possible_birthdays) != 1: 
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    if not unique_day(month, possible_birthdays):
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    if unique_month(month, possible_birthdays): 
        return False
    else: 
        return True 
```
