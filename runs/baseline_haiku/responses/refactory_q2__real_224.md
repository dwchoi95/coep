```python
def unique_day(day, possible_birthdays):
    count = 0
    for date in possible_birthdays:
        if date[1] == day:
            count += 1
    return count == 1

def unique_month(month, possible_birthdays):
    count = 0
    for mon in possible_birthdays:
        if mon[0] == month:
            count += 1
    return count == 1

def contains_unique_day(month, possible_birthdays):
    days_in_month = []
    for i in possible_birthdays:
        if i[0] == month:
            days_in_month.append(i[1])
    for day in days_in_month:
        if unique_day(day, possible_birthdays):
            return True
    return False
```
