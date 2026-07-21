You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Top-K
Write a function top_k that accepts a list of integers as the input and returns the greatest k number of values as a list, with its elements sorted in descending order. You may use any sorting algorithm you wish, but you are not allowed to use sort and sorted.

The solution must be a Python function named `top_k`.

## Visible test suite
assert top_k([9, 9, 4, 9, 7, 9, 3, 1, 6], 5) == [9, 9, 9, 9, 7]
assert top_k([9, 8, 4, 5, 7, 2, 3, 1, 6], 5) == [9, 8, 7, 6, 5]
assert top_k([4, 5, 2, 3, 1, 6], 6) == [6, 5, 4, 3, 2, 1]
assert top_k([4, 5, 2, 3, 1, 6], 3) == [6, 5, 4]
assert top_k([4, 5, 2, 3, 1, 6], 0) == []

## Example repairs from past students of THIS assignment
### Example 1: buggy submission
```python
def sort_age(lst):
        new=[]
        while lst !=[]:
            big=lst[0]
            for i in lst:
                if i[1]>big[1]:
                    big=i
            lst.remove(big)
            new.append(big)
        return new
def top_k(lst, k):
    return sort_age(lst)[:k]
    pass

```
### Example 1: corrected version
```python
def magus_sort(lst):
    if len(lst) == 0:
        return []
    elif len(lst) == 1:
        return lst
    elif len(lst) == 2:
        if lst[0] >= lst[1]:
            return lst
        else:
            return [lst[1], lst[0]]
    else:
        if lst[0] >= lst[1]:
            list1, list2 = [lst[0]], [lst[1]]
        else:
            list1, list2 = [lst[1]], [lst[0]]
        for i in lst[2:]:
            if i >= list1[0]:
                list1.append(i)
            else:
                list2.append(i)
        return magus_sort(list1) + magus_sort(list2)

def top_k(lst, k):
    return magus_sort(lst)[0:k]

```
### Example 2: buggy submission
```python
def top_k(lst, k):
    
    if lst == []:
        return lst
    
    lower = []
    higher = []
    plist = []
    
    pivot = lst[0]
    for e in lst:
        if e < pivot:
            lower.append(e)
        if e == pivot:
            plist.append(e)
        if e > pivot:
            higher.append(e)
    sort_list = lower + plist + higher
    sort_list = sort_list[::-1]
    
    if k == len(lst):
        return sort_list[:k-1]
    elif k > len(lst):
        return sort_list
    else:
        return sort_list[:k]

```
### Example 2: corrected version
```python
def magus_sort(lst):
    if len(lst) == 0:
        return []
    elif len(lst) == 1:
        return lst
    elif len(lst) == 2:
        if lst[0] >= lst[1]:
            return lst
        else:
            return [lst[1], lst[0]]
    else:
        if lst[0] >= lst[1]:
            list1, list2 = [lst[0]], [lst[1]]
        else:
            list1, list2 = [lst[1]], [lst[0]]
        for i in lst[2:]:
            if i >= list1[0]:
                list1.append(i)
            else:
                list2.append(i)
        return magus_sort(list1) + magus_sort(list2)

def top_k(lst, k):
    return magus_sort(lst)[0:k]

```
### Example 3: buggy submission
```python
def top_k(lst, k):
    sort, output = [], []
    while lst:
        largest = lst[0]
        for i in lst:
            if i > largest:
                largest = i
        lst.remove(largest)
        sort.append(largest)
    for j in sort:
        output.append(j)
        if len(output) == k:
            break
    return output    

```
### Example 3: corrected version
```python
def top_k(lst, k):
    rs=[]
    for qwerty in range(0,k):
        biggest=lst[0]
        for k in lst:
            if biggest<k:
                biggest=k
        rs.append(biggest)
        lst.remove(biggest)
    return rs

```
### Example 4: buggy submission
```python
def top_k(lst, k):
    new = []
    while len(lst) > len(lst) - k:
        new.append(lst.remove(max(lst)))
        
    return new
        

```
### Example 4: corrected version
```python
def top_k(lst, k):
    s = []
    for i in range(k):
        t = 0
        for r in lst:
            if r >= t:
                t = r
        lst.remove(t)
        s.append(t)
    return s

```
### Example 5: buggy submission
```python
def top_k(lst, k):
    sotsot = []
    while lst:
        while len(sotsot) <=k:
            sotsot.append(max(lst))
            lst.remove(max(lst)) #wont return u any value just modified the list only.
        return sotsot 
    

```
### Example 5: corrected version
```python
def top_k(lst, k):
    # Fill in your code here
    new = []
    for i in range(k):
        a = max(lst)
        lst.remove(a)
        new.append(a)
    return new
        

```

## Buggy student submission
```python
def top_k(lst, k):
    new = []
    while len(lst) > len(lst) - k:
        top = max(lst) 
        new.append(top)
        lst.remove(top)
        
    return new
        

```

## Observed failures when running the submission
- top_k([9, 9, 4, 9, 7, 9, 3, 1, 6], 5) expected [9, 9, 9, 9, 7] but got ValueError: max() arg is an empty sequence
- top_k([9, 8, 4, 5, 7, 2, 3, 1, 6], 5) expected [9, 8, 7, 6, 5] but got ValueError: max() arg is an empty sequence
- top_k([4, 5, 2, 3, 1, 6], 6) expected [6, 5, 4, 3, 2, 1] but got ValueError: max() arg is an empty sequence
- top_k([4, 5, 2, 3, 1, 6], 3) expected [6, 5, 4] but got ValueError: max() arg is an empty sequence

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
