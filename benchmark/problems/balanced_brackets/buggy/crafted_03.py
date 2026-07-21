def balanced_brackets(s):
    stack = []
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in ")]}":
            stack.pop()
    return len(stack) == 0
