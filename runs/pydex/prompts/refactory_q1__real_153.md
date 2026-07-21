You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Sequential Search

The solution must be a Python function named `search`.

## Visible test suite
assert search(42, [-5, 1, 3, 5, 7, 10]) == 6
assert search(42, [1, 5, 10]) == 3
assert search(5, [1, 5, 10]) == 1
assert search(7, [1, 5, 10]) == 2
assert search(3, [1, 5, 10]) == 1
assert search(-5, [1, 5, 10]) == 0
assert search(10, [-5, -1, 3, 5, 7, 10]) == 5
assert search(-100, [-5, -1, 3, 5, 7, 10]) == 0
assert search(0, [-5, -1, 3, 5, 7, 10]) == 2
assert search(100, []) == 0
assert search(-100, []) == 0

## Example repairs from past students of THIS assignment
### Example 1: buggy submission
```python
def search(x, seq):
    if seq == () or seq == []:
        return 0
    elif x <= seq[0]:
        return 0
    elif x >= seq[-1]:
        return len(seq) - 1
    else:
        seq_enum = [i for i in enumerate(seq)]
        for j in range(len(seq_enum) - 1):
            if x >= seq_enum[j][1] and x <= seq_enum[j+1][1]:
                return j+1

```
### Example 1: corrected version
```python
def search(x, seq):
    for i, e in enumerate(seq):
        if x <= e:
            return i
    return len(seq)


```
### Example 2: buggy submission
```python
def search(x, seq):
    for i in range (len(seq)):
        if x < seq[i]:
            return i
        elif x ==seq[i]:
            return i
        else:
            continue
    return i + 1

```
### Example 2: corrected version
```python
def search(x, seq):
    if len(seq) == 0:
            return 0
    else:
        for i, elem in enumerate(seq):
            if i == 0 and x < elem:
                return 0
            elif x <= elem:
                return i
            elif i == len(seq) - 1:
                return len(seq)

```
### Example 3: buggy submission
```python
def search(x, seq):
    for i, elem in enumerate(seq):
        if x <= elem:
            return i
        elif i == len(seq) - 1 and x > elem:
            return i + 1

```
### Example 3: corrected version
```python
def search(x, seq):
    lst = list(seq)
    lst.append(x)
    sort = []
    while lst:
        smallest = lst[0]
        for ele in lst:
            if ele < smallest:
                smallest = ele
        lst.remove(smallest)
        sort.append(smallest)
    for i in range(len(sort)):
        if sort[i] ==x:
            return i

```
### Example 4: buggy submission
```python
def search(x, seq):
    if len(seq)==0:
        return 0
    else:
        if x <= seq[0]:
            return 0
        elif x >= seq[-1]:
            return len(seq)
        else:
            for i in range(0, len(seq)-1):
                if seq[i] <= x <= seq[i+1]:
                    return i+1

```
### Example 4: corrected version
```python
def search(x, seq):
    if seq == () or seq == []:
        return 0
    else:
        for i, elem in enumerate(seq):
            if x <= elem:
                return i
            elif x > seq[len(seq)-1]:
                return len(seq)

```
### Example 5: buggy submission
```python
def search(x, seq):
    for i in range(len(seq)):
        if seq[i] < x:
            continue
        elif seq[len(seq)-1] < x:
            return len(seq)-1
        else:
            return i
    """ Takes in a value x and a sorted sequence seq, and returns the
    position that x should go to such that the sequence remains sorted """

```
### Example 5: corrected version
```python
def search(x, seq):
    if seq == [] or seq == ():
        return  0
    if x <= seq[0]:
        position = 0
    if x >= seq[len(seq) - 1]:
        position = len(seq)
    for i in range(len(seq)):
        if x <= seq[i] and x > seq[i-1]:
            position = i
    return position


```

## Buggy student submission
```python
def search(x, seq):
    for i in range(len(seq)):
        if x <= seq[i]:
            return seq.index(seq[i])
        elif seq[-1] <  x:
            return seq.index(seq[-1])+1


```

## Observed failures when running the submission
- search(100, []) expected 0 but got null
- search(-100, []) expected 0 but got null

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
