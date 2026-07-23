import math

k = 50

if k%2:
    print(math.floor(k/2)*math.ceil(k/2))
else:
    print(int((k/2)**2))