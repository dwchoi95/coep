x, y, a, b, c = [int(i) for i in input().split()]
pa = [int(i) for i in input().split()]
pb = [int(i) for i in input().split()]
pc = [int(i) for i in input().split()]

pa = sorted(pa, reverse=True)
pa = pa[:x]
pb = sorted(pb, reverse=True)
pb = pb[:y]
pc = sorted(pc, reverse=True)

l = pa + pb
l = sorted(l, reverse=True)

for i in range(len(pc)):
  for j in range(len(l)):
    if pc[i] > l[j]:
      l[j] = pc[i]
  if j == len(l)-1:
    break
      
print(sum(l))
  