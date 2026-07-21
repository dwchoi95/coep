```python
def unique_day(date, possible_birthdays):
    if [b[1] for b in possible_birthdays].count(date) != 1: 
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    if [b[0] for b in possible_birthdays].count(month) != 1:
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    if not any(unique_day(b[1], possible_birthdays) for b in possible_birthdays if b[0] == month): 
        return False
    else: 
        return True 
```
