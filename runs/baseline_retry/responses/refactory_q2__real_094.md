```python
def unique_day(date, possible_birthdays):
    result = 0
    for i in possible_birthdays:
        if date == i[1]:
            result += 1
    if result == 1:
        return True
    else:
        return False
    

def unique_month(month, possible_birthdays):
    return str(possible_birthdays).count(month) == 1

def contains_unique_day(month, possible_birthdays):
    return month in possible_birthdays[1]
```
