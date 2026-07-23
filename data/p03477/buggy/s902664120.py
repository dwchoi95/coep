A, B, C, D = map(int, input().split())
 
if A + B == C + D:
  r = 'Balanced'
if A + B > C + D:
  r = 'Left'
else:
  r = 'Right'
print(r)