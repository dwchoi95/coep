import decimal

S = input()

ans = decimal.Decimal("inf")
for i in range(len(S)-1):
    if S[i] != S[i+1]:
        ans = min(ans, max(i, len(S)-i))

print(ans)
