a,b,c = input().split()
n = 0
if a[len(a)-1] == b[0] and b[len(b)-1] == c[0]:
    print('YES')
else:
    print('NO')