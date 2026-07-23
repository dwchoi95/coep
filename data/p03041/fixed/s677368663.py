


n, k = map(int, input().split())

s = list(input())


a = s[k-1:k]

a = ','.join(a)

a = a.lower()

s[k-1:k] = a

s = ''.join(s)

print("{}".format(s))
