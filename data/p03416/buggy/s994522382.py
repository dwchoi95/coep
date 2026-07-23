A, B = map(int, input().split())

cnt = 0
for n in range(A, B + 1):
    s = str(n)
    if s[:2] == s[3:]:
        cnt += 1

print(cnt)
