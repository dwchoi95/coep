```python
def unique_day(date, possible_birthdays):
    j = 0
    for i in possible_birthdays:
        if date == i[1]:
            j = j+1
        else:
            j = j
    if j == 1:
        return True
    else:
        return False

def unique_month(month, possible_birthdays):
    j = 0
    for i in possible_birthdays:
        if month == i[0]:
            j = j+1
        else:
            j = j
    if j == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    days_in_month = []
    for i in possible_birthdays:
        if month == i[0]:
            days_in_month.append(i[1])
    for day in days_in_month:
        if unique_day(day, possible_birthdays):
            return True
    return False
```
