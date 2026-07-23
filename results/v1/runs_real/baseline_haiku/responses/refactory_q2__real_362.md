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
    i = 0
    for m in possible_birthdays:
        if month == m[0]:
            i += 1
    if i == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    for i in possible_birthdays:
        if month == i[0]:
            if unique_day(i[1], possible_birthdays):
                return True
    return False
```
