s = list(input().split())
if s[0] == s[1]:
  print(int(s[2]))
elif s[1] == s[2]:
  print(int(s[0]))
else:
  print(int(s[1]))