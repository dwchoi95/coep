from collections import defaultdict
def Z(S):
    res = [0]*len(S)
    res[0] = len(S)
    i = 1
    j = 0
    while i < len(S):
        while i+j < len(S) and S[j] == S[i+j]:
            j += 1
        res[i] = j
        if j == 0:
            i += 1
            continue
        k = 1
        while i+k < len(S) and k+res[k] < j:
            res[i+k] = res[k]
            k += 1
        i += k
        j -= k
    return res

class UnionFind:
    def __init__(self, num):
        self.table = [-1 for _ in range(num)]

    def find(self, x):
        if self.table[x] < 0:
            return x
        else:
            self.table[x] = self.find(self.table[x])
            return self.table[x]

    def union(self, x, y):
        s1 = self.find(x)
        s2 = self.find(y)

        if s1 != s2:
            if self.table[s1] <= self.table[s2]:
                self.table[s1] += self.table[s2]
                self.table[s2] = s1
            else:
                self.table[s2] += self.table[s1]
                self.table[s1] = s2
            return True
        return False

s = input()
t = input()

S = s*(len(t)
z = Z(t+'*'+S)
z = z[len(t)+1:]

u = UnionFind(len(s))

for i in range(len(s)):
    j = (i+len(t))%len(s)
    if z[i] == len(t) and z[j] == len(t):
        u.union(i,j)

d = defaultdict(list)
for i in range(len(s)):
    if z[i] == len(t):
        d[u.find(i)].append(i)

ans = 0
for k in d:
    loop = True
    if len(d[k])==1:
        loop = len(t)%len(s)==0
    else:
        for i in d[k]:
            j = (i+len(t)*(len(d[k])-1))%len(s)
            loop = z[j]==len(t) and loop
    if loop:
        ans = -1
        break
    ans = max(ans,len(d[k]))

print(ans)