```python
def balanced_brackets(s):
    br = [c for c in s if c in '()[]{}']
    closing = {'(': ')', '[': ']', '{': '}'}

    def parse(i):
        while i < len(br) and br[i] in closing:
            want = closing[br[i]]
            i = parse(i + 1)
            if i is None or i >= len(br) or br[i] != want:
                return None
            i += 1
        return i
    return parse(0) == len(br)
```
