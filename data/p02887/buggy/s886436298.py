N = int(input())
S = input()

S = S + 'A'
last = S[0]
cnt = 0
for s in S[1:]:
    if last == s:
        continue
    else:
        cnt += 1
        last = s
print(cnt-1)