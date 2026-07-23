s = list(input())
w = int(input())
index = 0
l = []
while index <= len(s) - 1:
  print(index)
  l.append(s[index])
  index += w
print(*l, sep="")