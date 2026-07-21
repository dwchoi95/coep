def balanced_brackets(s):
    depth = 0
    for c in s:
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                return False
            depth -= 1
    return depth == 0
