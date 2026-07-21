```python
def unique_day(date, possible_birthdays):
    tpl = ()
    for i in possible_birthdays:
        tpl += (i[1],)
    if tpl.count(date) > 1 or tpl.count(date) == 0:
        return False
    return True    

def unique_month(month, possible_birthdays):
    tpl = ()
    for j in possible_birthdays:
        tpl += (j[0],)
    if tpl.count(month) > 1 or tpl.count(month) == 0:
        return False
    return True    

def contains_unique_day(month, possible_birthdays):
    for i in possible_birthdays:
        if i[0] == month:
            if unique_day(i[1], possible_birthdays):
                return True
    return False
```
