A,B,K=(int(x) for x in input().split())

val = 1
valSet = []
while True:
  if A % val == 0 and B % val == 0:
    valSet.append(val)
  val += 1
  if val > min(A, B):
    break
print(valSet[-1*K])
