


n, k = map(int, input().split())


s = list(input())

a = s[k:k+1]

a = ','.join(a)

a = a.lower()

s[k:k+1] = a

print(s)