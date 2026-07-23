def balanced_brackets(s):
    opens = 0
    closes = 0
    for c in s:
        if c in "([{":
            opens += 1
        elif c in ")]}":
            closes += 1
    return opens == closes
