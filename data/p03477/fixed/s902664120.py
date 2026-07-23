A, B, C, D = map(int, input().split())
 
if (A + B) == (C + D):
  r = 'Balanced'
elif (A + B) > (C + D):
  r = 'Left'
elif (A + B) < (C + D):
  r = 'Right'
print(r)