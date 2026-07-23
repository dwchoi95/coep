import sys
input = sys.stdin.readline
X, Y = map(int, input().split())
for i in range(101):
  j = X - i
  if i * 2 + j * 4 == Y:
    print("Yes")
    exit(0)
print("No")