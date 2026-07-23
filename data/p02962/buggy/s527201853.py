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

from collections import defaultdict
class UnionFind:
    def __init__(self, num):
        self.table = [-1 for _ in range(num)]
        self.sz = defaultdict(lambda:1)

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
            size = self.sz[s1]+self.sz[s2]
            if self.table[s1] <= self.table[s2]:
                self.table[s1] += self.table[s2]
                self.table[s2] = s1
            else:
                self.table[s2] += self.table[s1]
                self.table[s1] = s2
            s = self.find(x)
            self.sz[s] = size
            return True
        return False

    def size(self, x):
        s = self.find(x)
        return self.sz[s]

s = input()
t = input()

S = ''
while len(S) <= len(t):
    S = S + s
S = S + S
z = Z(t+'*'+S+S)
z = z[len(t)+1:]
u = UnionFind(len(z))
ans = 0
for i in range(len(z)-len(t)):
    if z[i]==len(t) and z[i+len(t)]==len(t):
        u.union(i,i+len(t))
        if i+len(t) < len(S):
            ans = max(u.size(i),ans)
        else:
            if u.size(i) > ans:
                ans = -1

print(ans)