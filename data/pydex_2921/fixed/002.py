# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
from scipy import linalg
import numpy as np
A=eval(input())
B=eval(input())
a=np.array(A)
b=np.array(B)
try:
    x=linalg.solve(a,b)
except Exception as e:
    print('ERROR: Cannot find solution.')
else:
    print(x)