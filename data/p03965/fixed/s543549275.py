s = input()
n = len(s)

s = [i for i in s]
for i in range(n):
    if s[i] == "p":
        s[i] = 1
    else:
        s[i] = 0

d = [0]*n
d[0] = 0
gc = 1
pc = 0
for i in range(1, n):
    if gc-1 >= pc:
        d[i] = 1
        pc += 1
    else:
        d[i] = 0
        gc += 1

ans = 0
for i in range(n):
    ans += d[i]-s[i]

print(ans)