```python
def unique_day(day, possible_birthdays):
    counter=0
    for i in possible_birthdays:
        if day==i[1]:
            counter+=1
    return counter==1

def unique_month(month, possible_birthdays):
    counter=0
    for i in possible_birthdays:
        if month==i[0]:
            counter+=1
    return counter==1

def contains_unique_day(month, possible_birthdays):
    result=()
    for i in possible_birthdays:
        if i[0]==month:
            result+=(i,)
    for i in result:
        if unique_day(i[1],possible_birthdays)==True:
            return True
    return False
```
