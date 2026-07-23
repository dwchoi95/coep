N = int(input())
kuku = [1, 2, 3, 4, 5, 6, 7, 8, 9]
kuku1 = [a * b for a in kuku for b in kuku]
if N in kuku:
  print("Yes")
else:
  print("No")