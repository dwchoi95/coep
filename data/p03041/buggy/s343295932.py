N, K = list(map(int, input().split()))
s = input()
print(s.replace(s[K - 1], s[K - 1].lower()))