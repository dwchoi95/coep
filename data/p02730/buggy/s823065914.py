s = list(str(input()))
n = len(s)
N = int((n-1)/2)
M = int((n+3)/2)
l = []
m = []
for i in range(N):
    l.append(s[i])
for i in range (M-1,N):
    m.append(s[i])
a = ''.join(l)
b = ''.join(m)
l.reverse()
m.reverse()
A = ''.join(l)
B = ''.join(m)
if (a==A and b==B):
    print('Yes')
else:
    print('No')