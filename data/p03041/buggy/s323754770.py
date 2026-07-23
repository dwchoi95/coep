n, k = map(int, input().split())
s = input()
t = s[k-1]
ans = s[:k-1] + t.lower() + s[k:]
