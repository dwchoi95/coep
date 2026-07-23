n = int(input())

for _ in range(n):
    xa, ya, ra, xb, yb, rb = map(float, input().split())
    dist = ((xa - xb)**2 + (ya - yb)**2)**.5
    if ra + rb < dist:
        print('0')
    elif (rb < ra) and (dist < ra):
        print('2')
    elif (ra < rb) and (dist < rb):
        print('-2')
    else:
        print('1')