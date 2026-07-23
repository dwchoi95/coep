A, B = map(int, input().split())
count = 0
for i in range(A, B + 1):
  i = str(i)
  if i[:2] == i[::-1][:2] :
    count += 1
print(count)