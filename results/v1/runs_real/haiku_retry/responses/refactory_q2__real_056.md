```python
def unique_day(date, possible_birthdays):
    result=()
    counter=0
    for i in possible_birthdays:
        if date==i[1]:
            result=result+(possible_birthdays[:counter]+possible_birthdays[counter+1:])
            break
        else:
            counter+=1
            continue
    for i in result:
        if date==i[1]:
            return False
    return True

def unique_month(month, possible_birthdays):
    result=()
    counter=0
    for i in possible_birthdays:
        if month==i[0]:
            result=result+(possible_birthdays[:counter]+possible_birthdays[counter+1:])
            break
        else:
            counter+=1
            continue
    for i in result:
        if month==i[0]:
            return False
    return True

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
