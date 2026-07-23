n = int(input())

ln = []

for i in range(9):
  for j in range(9):
    ln.append(i*j)
    
print("Yes" if n in ln else "No")