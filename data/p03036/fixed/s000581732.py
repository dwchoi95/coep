r, D, x_2000= map(int, input().split(' '))
xs = [x_2000]
for x in range(10):
	xs.append(r*xs[len(xs)-1]-D)
xs.pop(0)
print('\n'.join(map(str, xs)))