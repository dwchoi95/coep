S = input().strip()

count = 0
suma = 0
for i in S:
  if i=="W":
    suma += count
  else:
    count += 1
print(suma)