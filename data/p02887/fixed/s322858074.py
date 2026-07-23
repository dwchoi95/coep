n = int(input())
s = input()
a = 1
for i in range(n-1):
  if s[i] != s[i+1]:
    a += 1
print(a)