```python
def unique_day(day, possible_birthdays):
    i = 0
    for days in possible_birthdays:
        if int(day) == int(days[1]):
            i += 1
        
    if i == 1:
        return True
    else:
        return False

def unique_month(month, possible_birthdays):
    return sum(month in months for months in possible_birthdays) == 1

def contains_unique_day(month, possible_birthdays):
    return not unique_month(month, possible_birthdays)
```
