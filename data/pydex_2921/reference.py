import numpy as np
from scipy import linalg

a = eval(input())
b = eval(input())
A = np.array(a)
B = np.array(b)

try:
    x = linalg.solve(a, b)
except:
    print('ERROR: Cannot find solution.')
else:
    print(x)
