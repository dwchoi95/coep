n = int(input())
s = input()
cur = s[0]
l = []
for i in range(n - 1):
    if cur != s[i + 1]:
        l.append(cur)
        cur = s[i + 1]
l.append(cur)
print(len(l))