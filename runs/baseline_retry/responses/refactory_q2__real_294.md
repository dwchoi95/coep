```python
def unique_day(day, possible_birthdays):
    total= 0
    for i in possible_birthdays:
        if day == i[1]:
            total= total + 1
    return total == 1

def unique_month(month, possible_birthdays):
    return sum(month in i for i in possible_birthdays) == 1

def contains_unique_day(month, possible_birthdays):
    return not unique_month(month, possible_birthdays)
```
