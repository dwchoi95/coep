```python
def unique_day(date, possible_birthdays):
    list_final = [possible_birthdays[i][1] for i in range(0,len(possible_birthdays))]
    list_final = sorted(list_final)
    if list_final.count(date) == 1:
        return True
    else:
        return False
                
def unique_month(month, possible_birthdays):
    list = [possible_birthdays[i][0] for i in range(0,len(possible_birthdays))]
    list = sorted(list)
    if list.count(month) == 1:
        return True
    else:
        return False

def contains_unique_day(month, possible_birthdays):
    month_tuple = ()
    for i in range(0,len(possible_birthdays)):
        if possible_birthdays[i][0] == month:
            month_tuple = month_tuple + (possible_birthdays[i][1],)
    for x in month_tuple:
        if unique_day(x, possible_birthdays):
            return True
    return False
```
