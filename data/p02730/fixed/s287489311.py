s = input()
n = len(s)
a = int((n-1)/2)
b = int((n+3)/2)
x=s[:a]
y = s[b-1:]
if x==x[::-1] and y==y[::-1] and s==s[::-1]:
  print("Yes")
else:
  print("No")
