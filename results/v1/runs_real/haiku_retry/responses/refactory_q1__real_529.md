```python
def search(x, seq):
    """ Takes in a value x and a sorted sequence seq, and returns the
    position that x should go to such that the sequence remains sorted """
    if len(seq) == 0:
        return 0
    counter = -1
    for i in seq:
        if x <= i:
            counter += 1
            return counter
        else:
            counter += 1
    if x > seq[counter]:
        return counter + 1
```
