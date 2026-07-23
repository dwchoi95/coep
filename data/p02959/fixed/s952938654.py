N = int(input())
A_list = list(map(int, input().split()))
B_list = list(map(int, input().split()))

taos = 0
keep = 0

for i, (a, b) in enumerate(zip(A_list, B_list)):
  if a >= (b + keep) :
    taos += (b + keep)
    keep = 0
  else:
    taos += a
    if keep > a:
      keep = b
    else:
      keep = (b + keep) - a 
  

if A_list[-1] >= keep:
  taos += keep
else:
  taos += A_list[-1]
print(taos)