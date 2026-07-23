```python
def unique_day(date, possible_birthdays):
    count=0
    for i in possible_birthdays: 
        if i[1]==date:
            count+=1
    if count!=1:
        return False
    else:
        return True

def unique_month(month, possible_birthdays):
    count=0
    for i in possible_birthdays:
        if i[0]==month:
            count+=1
    if count!=1:
        return False
    else:
        return True

def contains_unique_day(month, possible_birthdays):
    for i in possible_birthdays:
        if i[0]==month and unique_day(i[1], possible_birthdays):
            return True
    return False
```
