```python
def unique_day(day, possible_birthdays):
    x = 0
    for i in possible_birthdays:
        if day == i[1]:
            x = x + 1
        else:
            x = x
    if x == 1:
        return True
    else:
        return False
        
def unique_month(month, possible_birthdays):
    x = 0
    for i in possible_birthdays:
        if month == i[0]:
            x = x + 1
        else:
            x = x
    if x == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    y = ()
    for i in possible_birthdays:
        if i[0] == month:
            y = y + (i, )
    for a in y:
        if unique_day(a[1], possible_birthdays):
            return True
    return False
```
