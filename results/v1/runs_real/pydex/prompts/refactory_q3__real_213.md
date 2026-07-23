You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Duplicate elimination
Write a function remove_extras(lst) that takes in a list and returns a new list with all repeated occurrences of any element removed. For example, remove_extras([5, 2, 1, 2, 3]) returns the list [5, 2, 1, 3].

The solution must be a Python function named `remove_extras`.

## Visible test suite
assert remove_extras([1, 1, 1, 2, 3]) == [1, 2, 3]
assert remove_extras([1, 5, 1, 1, 3, 2]) == [1, 5, 3, 2]
assert remove_extras([]) == []
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]

## Example repairs from past students of THIS assignment
### Example 1: buggy submission
```python
def remove_extras(lst):
    for num in lst:
        while lst.count(num)>1:
            lst.remove(num)
    return lst

```
### Example 1: corrected version
```python
def remove_extras(lst):
    new = []
    for el in lst:
        if el not in new:
            new += [el,]
    return new

```
### Example 2: buggy submission
```python
def remove_extras(lst):
    a = ()
    n = len(lst)
    for i in range(n):
        for j in range(i,n):
            if lst[i] == lst[j] and i != j:
                a += (lst[j],)
            else:
                continue
    c = a[:-1]
    b = lst[::-1]
    for i in range(len(c)):
        b.remove(c[i])
    d = b[::-1]
    return d

```
### Example 2: corrected version
```python
def remove_extras(lst):
    new_lst = []
    for ele in lst:
        if not (ele in new_lst):
            new_lst.insert(len(new_lst), ele)
    return new_lst
    

```
### Example 3: buggy submission
```python
def remove_extras(lst):
    for i in range (0, len(lst)):
        for j in range (i + 1, len(lst)):
            if lst[j] == lst[i]:
                lst.pop(j)
                print (lst)
            else:
                continue
            return remove_extras(lst)

```
### Example 3: corrected version
```python
def remove_extras(lst):
    # your code here
    lst_new = []
    for element in lst:
        if element not in lst_new:
            lst_new.append(element)
    return lst_new

```
### Example 4: buggy submission
```python
def remove_extras(lst):
    listt = lst.reverse()
    for element in listt:
        if listt.count(element) > 1:
            listt.remove(element)
    return listt.reverse()

```
### Example 4: corrected version
```python
def remove_extras(lst):
    result = []
    for i in lst:
        if i not in result:
            result.append(i)
    return result
    pass

```
### Example 5: buggy submission
```python
def remove_extras(lst):
    new_list = ()
    for x in lst:
        if x not in new_list:
            new_list += ((x))
    return new_list

```
### Example 5: corrected version
```python
def remove_extras(lst):
    new = []
    for x in lst:
        if x not in new:
            new += [x]
    return new
    

```

## Buggy student submission
```python
def remove_extras(lst):
    new_list = []
    for element in lst:
        if element in new_list:
            continue
        else:
            new_list += new_list.append(element)

```

## Observed failures when running the submission
- remove_extras([1, 1, 1, 2, 3]) expected [1, 2, 3] but got TypeError: 'NoneType' object is not iterable
- remove_extras([1, 5, 1, 1, 3, 2]) expected [1, 5, 3, 2] but got TypeError: 'NoneType' object is not iterable
- remove_extras([]) expected [] but got null
- remove_extras([3, 4, 5, 1, 3]) expected [3, 4, 5, 1] but got TypeError: 'NoneType' object is not iterable
- remove_extras([3, 4, 5, 1, 3]) expected [3, 4, 5, 1] but got TypeError: 'NoneType' object is not iterable

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
