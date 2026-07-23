
S = input()


cn = S.count('N')
ce = S.count('E')
cs = S.count('S')
cw = S.count('W')

if cn > 0 and cs > 0 and ce == 0 and cw == 0:
    print('Yes')
elif cn == 0 and cs == 0 and ce > 0 and cw > 0:
    print('Yes')
elif cn > 0 and cs > 0 and ce > 0 and cw > 0:
    print('Yes')
else:
    print('No')
