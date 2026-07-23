s = input()
N = 0
S = 0
W = 0
E = 0
for i in range(len(s)) :
    str = s[i]
    if str == 'N' :
        N = 1
    elif str == 'S':
        S = 1
    elif str == 'W':
        W = 1
    elif str == 'E':
        E = 1
if (N-S)==0 and (W-E)==0 :
    print('YES')
else:
    print('NO')
