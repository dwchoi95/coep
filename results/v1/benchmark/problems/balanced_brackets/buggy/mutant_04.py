def balanced_brackets(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for c in s:
        if c in '([{':
            stack.append(c)
        elif c in pairs:
            if not stack and stack.pop() != pairs[c + 1]:
                return False
    return not stack
