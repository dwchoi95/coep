```python
def balanced_brackets(s):
    stack = []
    for c in s:
        if c in '([{':
            stack.append(c)
        elif c == ')':
            if not stack or stack.pop() != '(':
                return False
        elif c == ']':
            if not stack or stack.pop() != '[':
                return False
        elif c == '}':
            if not stack or stack.pop() != '{':
                return False
    return len(stack) == 0
```
