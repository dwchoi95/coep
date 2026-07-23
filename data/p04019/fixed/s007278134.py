S = input()

tmp = [0 for _ in range(4)]

res = 'Yes'
for i in range(len(S)):
    if S[i] == 'S':
        tmp[0] = 1
    elif S[i] == 'N':
        tmp[1] = 1
    elif S[i] == 'W':
        tmp[2] = 1
    else:
        tmp[3] = 1
        
if tmp[0] == 1 and tmp[1] == 0:
    res = 'No'
if tmp[1] == 1 and tmp[0] == 0:
    res = 'No'
if tmp[2] == 1 and tmp[3] == 0:
    res = 'No'
if tmp[3] == 1 and tmp[2] == 0:
    res = 'No'

print(res)

