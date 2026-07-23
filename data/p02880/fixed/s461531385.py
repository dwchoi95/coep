n = int(input())

ln = []

for i in range(1,10):
  for j in range(1,10):
    ln.append(i*j)
    
print("Yes" if n in ln else "No")