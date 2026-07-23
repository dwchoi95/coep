# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
from scipy import linalg
import numpy as np
arr = eval(input())
L = eval(input())
M = np.mat(arr)
try:
    sol = linalg.solve(M,L)
    print(sol)
except:
    print('ERROR: Cannot find solution.')