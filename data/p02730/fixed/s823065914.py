s = list(str(input()))

n = len(s)
N = int((n-1)/2)
M = int((n+3)/2)

l = []
m = []

for i in range(N):
    l.append(s[i])
    
for i in range (M-1,n):
    m.append(s[i])
    
a = ''.join(l)
l.reverse()
A = ''.join(l)

b = ''.join(m)
m.reverse()
B = ''.join(m)

t = s
t.reverse()
x = ''.join(s)
y = ''.join(t)

if (a==A and b==B and a == b):
    print('Yes')
else:
    print('No')