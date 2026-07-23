a, b, k = map(int, input().split())

n = 0
if a < b:
  n = a
else:
  n = b

cd_list = []
i = 1
while i <= n:
  if a % i == 0 and b % i == 0:
    cd_list.append(i)
  i += 1

cd_list.reverse()
print(cd_list[k-1])
