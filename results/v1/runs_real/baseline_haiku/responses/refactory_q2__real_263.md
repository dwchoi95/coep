```python
def unique_day(date, possible_birthdays):
    count = 0
    for entry in possible_birthdays:
        if date == entry[1]:
            count += 1
    return count == 1

def unique_month(month, possible_birthdays):
    count = 0
    for entry in possible_birthdays:
        if month == entry[0]:
            count += 1
    return count == 1

def contains_unique_day(month, possible_birthdays):
    for entry in possible_birthdays:
        if entry[0] == month:
            if unique_day(entry[1], possible_birthdays):
                return True
    return False
```
