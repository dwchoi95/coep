n = int(input())

for _ in range(n):
    xa, ya, ra, xb, yb, rb = map(float, input().split())
    dist = ((xa - xb)**2 + (ya - yb)**2)**.5
    if ra + rb < dist:
        print('0')
    elif abs(ra - rb) <= dist:
        print('1')
    elif (rb < ra):
        print('2')
    elif (ra < rb):
        print('-2')