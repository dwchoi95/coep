N = int(input())
A_list = list(map(int, input().split()))
B_list = list(map(int, input().split()))

A_0 = A_list.pop(0)


A_list[0] = A_list[0] + A_0


taos = 0
nokori = 0
keep = 0

for i, (a, b) in enumerate(zip(A_list, B_list)):
  if i == 0:
    if a >= b:
      taos += b
    else:
      taos += b-a
  else: 
    if (a + nokori) >= (b + keep) :
      taos += (b + keep)
      nokori = (a + nokori) - (b + keep)
      keep = 0
    else:
      taos += (a + nokori)
      nokori = 0
      keep = (b + keep) - (a + nokori)
 
print(taos)