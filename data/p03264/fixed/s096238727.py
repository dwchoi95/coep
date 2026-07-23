
k = int(input())        

if (k%2) == 1:
    o = (k-1) * (k+1) / 8
    
    print(int(2*o))

else:
    o = k * (k+2) / 8
    e = k * (k-2) / 8
    print(int(o+e))