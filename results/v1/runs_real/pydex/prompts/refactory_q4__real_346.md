You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Sorting Tuples
Can we sort items other than integers? For this question, you will be sorting tuples! We represent a person using a tuple (<gender>, <age>). Given a list of people, write a function sort_age that sorts the people and return a list in an order such that the older people are at the front of the list. An example of the list of people is [("M", 23), ("F", 19), ("M", 30)]. The sorted list would look like [("M", 30), ("M", 23), ("F", 19)]. You may assume that no two members in the list of people are of the same age.

The solution must be a Python function named `sort_age`.

## Visible test suite
assert sort_age([["F", 19]]) == [["F", 19]]
assert sort_age([["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18]]
assert sort_age([["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19]]
assert sort_age([]) == []

## Example repairs from past students of THIS assignment
### Example 1: buggy submission
```python
def sort_age(lst):
    youngest = lst[0][1]
    sorted = []
    while lst:
        for elem in lst:
            if elem[1] < youngest:
                youngest = elem[1]
        lst.remove(youngest)
        sorted.append(youngest)
    return sorted

```
### Example 1: corrected version
```python
def sort_age(lst):
    for i in range(len(lst)):
        position = i
        biggest = position
        for a in range(position, len(lst)):
            if lst[a][1] > lst[biggest][1]:
                biggest = a
        tmp = lst[position]
        lst[position] = lst[biggest]
        lst[biggest] = tmp
    return lst

```
### Example 2: buggy submission
```python
def sort_age(lst):
    a = lst
    sort = []
    while a:
        largest = a[0]
        for item in a:
            if item[1] >largest[1]:
                largest = item
        a.remove(largest)
        sort.append(largest)

    print(sort)# Fill in your code here
    

```
### Example 2: corrected version
```python
def sort_age(lst):
    
    people = []
    
    while lst:
        
        i = lst[0]
        
        for a in lst:
            
            if a[1] >= i[1] :
                
                i = a
                
        lst.remove(i)
        
        people.append(i)
        
    return people

```
### Example 3: buggy submission
```python
def sort_age(lst):
    decoy = []
    decoy2 = []
    final = []
    for i in lst:
        decoy.append(i[1])
    while decoy != []:
        decoy2.append(min(decoy))
        decoy.remove(min(decoy))
    for i in decoy2:
        for j in lst:
            if i == j[1]:
                final.append(j)
    return final
    
    

```
### Example 3: corrected version
```python
def sort_age(lst):
    l=lst.copy()
    res=[]
    while l:
        biggest=l[0]

        for element in l:
            if element[1]>biggest[1]:
                biggest=element
                
        l.remove(biggest)
        res.append(biggest)
    return res

```
### Example 4: buggy submission
```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while lst[i][1]<lst[i-1][1]:
            lst.pop(i)
            lst.insert(i-1,lst[i])# Fill in your code here
    return lst.reverse()

```
### Example 4: corrected version
```python
def sort_age(lst):
    total = ()
    def helper(i, tup):
        if tup == ():
            return (i,)
        elif i[1] > tup[0][1]:
            return (i,)+ tup
        else:
            return (tup[0],) + helper(i, tup[1:])
    for i in lst:
        if total == ():
            total = (i,)
        else:
            total = helper(i, total)
    return list(total)

```
### Example 5: buggy submission
```python
def sort_age(lst):
    current=0
    tup=()
    for i in lst:
        if i[1]>current:
            tup+=tuple(i)
            current=i[1]
        else:
            tuple(i)+tup
    return tup
            

```
### Example 5: corrected version
```python
def sort_age(lst):
    ans = []
    while lst:
        biggest = lst[0]
        for elem in lst:
            if elem[1] > biggest[1]:
                biggest = elem
        lst.remove(biggest)
        ans.append(biggest)
    
    return ans
    
    

```

## Buggy student submission
```python
def sort_age(lst):
    current=0
    tup=()
    for i in lst:
        if i[1]>current:
            tup+=tuple(i)
            current=i[1]
        else:
            tup=tuple(i)+tup
    return tup
            

```

## Observed failures when running the submission
- sort_age([["F", 19]]) expected [["F", 19]] but got ["F", 19]
- sort_age([["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) expected [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]] but got ["M", 17, "M", 30, "F", 19, "M", 23, "F", 18, "M", 35]
- sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) expected [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]] but got ["M", 17, "F", 19, "F", 18, "M", 23, "M", 30]
- sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30]]) expected [["M", 30], ["M", 23], ["F", 19], ["F", 18]] but got ["F", 19, "F", 18, "M", 23, "M", 30]
- sort_age([["M", 23], ["F", 19], ["M", 30]]) expected [["M", 30], ["M", 23], ["F", 19]] but got ["F", 19, "M", 23, "M", 30]

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
