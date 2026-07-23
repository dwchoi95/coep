N, M = map(int,input().split())

A = []
for i in range(N):
  a,b = map(int,input().split())
  A.append([a,b])

A.sort()


nokori = M
yen = 0
mise = 0
while nokori > 0:
  if A[mise][1] >= nokori: 
    yen += A[mise][0]*nokori
    break
  else:
    yen += A[mise][0]*A[mise][1]
    nokori -= A[mise][1]
    mise += 1
print(yen)
  