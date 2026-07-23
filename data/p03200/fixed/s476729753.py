S = input()


idx_w = 0
idxes_b = []

for i, s in enumerate(S):
    if s == 'B':
        idxes_b.append(i)
    elif s == 'W':
        idx_w = i

idxes_b = [b for b in idxes_b if idx_w > b]

ans = 0
for i, b in enumerate(idxes_b[::-1]):
    ans += idx_w - b - i

print(max(0, ans))