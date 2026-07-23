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
