A, B = map(int, input().split())
a, c = 0, 1
while c < B:
  c += A - 1
  a += 1
print(a)