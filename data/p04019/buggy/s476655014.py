s = input()
ans = 'Yes'
n = 0
w = 0
sow = 0
e = 0

for i in range(len(s)):
    if s[i] == 'N':
        n += 1
    elif s[i] == 'W':
        w += 1
    elif s[i] == 'S':
        sow += 1
    else:
        e += 1



if (n == 0 and w != 0) or (n != 0 and w == 0):
    ans = 'No'
if (sow == 0 and e != 0) or (sow != 0 and e == 0):
    ans = 'NO'
print(ans)