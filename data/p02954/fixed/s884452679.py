S = input()

even = 0
odd = 0
l = S.index('L')
r = S.index('R')
ans = [0] * len(S)

for i in range(len(S) - 1):
    if i % 2 == 0:
        even += 1
    else:
        odd += 1
    if S[i] == 'R' and S[i + 1] == 'L':
        l = i
        r = i + 1
        if i % 2 == 0:
            ans[i] += even
            ans[i + 1] += odd
        else:
            ans[i] += odd
            ans[i + 1] += even
        even = 0
        odd = 0
    elif S[i] == 'L' and S[i + 1] == 'R':
        if l % 2 == 0:
            ans[l] += even
            ans[l + 1] += odd
        else:
            ans[l] += odd
            ans[l + 1] += even
        even = 0
        odd = 0


if (len(S) - 1 - l) % 2 == 0:
    ans[l] += 1
else:
    ans[r] += 1

if l % 2 == 0:
    ans[l] += even
    ans[l + 1] += odd
else:
    ans[l] += odd
    ans[l + 1] += even

print(' '.join(map(str, ans)))