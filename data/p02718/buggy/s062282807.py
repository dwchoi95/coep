N, M = list(map(int, input().split()))
scores = list(map(int, input().split()))
at_least = sum(scores) 

if len([ s for s in scores if s > at_least]) >= M:
  print('Yes')
else:
  print('No')