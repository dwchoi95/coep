k = int(input())        
if (k%2) == 1:
    oe = ((k+1) * (k-3)) / 8
    print(2 * oe)
else:
    o = (k+2) * (k-1)/8
    e = (k*(k-4))/8
    print(o+e)