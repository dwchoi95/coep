s = input()
score = 0
toUse = 0
for it in s:
  if it == 'g' and toUse > 0:
    toUse -= 1
    score += 1
    continue
  if it == 'g':
    continue
  if toUse > 0:
    toUse -= 1
  else:
    score -=1
    
print(score)
