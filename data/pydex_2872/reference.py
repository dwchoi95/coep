inp = input()

ni = inp.find('not')
bi = inp.find('bad')
if ni == -1:
    # 'not' not found.
    print(inp)
elif bi == -1:
    # 'bad' not found
    print(inp)
elif ni > bi:
    # 'not' after 'bad'
    print(inp)
else:
    # all conditions satisfied.
    bi = bi + len('bad')
    op = inp[:ni] + 'good' + inp[bi:]
    print(op)
    