x, y, a, b, c = [int(i) for i in input().split()]
pa = [int(i) for i in input().split()]
pb = [int(i) for i in input().split()]
pc = [int(i) for i in input().split()]

pa = sorted(pa, reverse=True)
pa = pa[:x]
pb = sorted(pb, reverse=True)
pb = pb[:y]
pc = sorted(pc, reverse=True)

l = pa + pb + pc
l = sorted(l, reverse=True)
l = l[:int(x+y)]
print(sum(l))