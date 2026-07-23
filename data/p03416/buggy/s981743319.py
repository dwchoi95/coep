A, B = map(int, input().split())
count = 0
for i in range(A, B):
  i = str(i)
  if i[:2] == i[-2:] :
    count += 1
print(count)