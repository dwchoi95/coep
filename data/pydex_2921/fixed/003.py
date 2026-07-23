# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
from scipy import linalg
import numpy as np
first = input()
first = eval(first)
second = input()
second = eval(second)
a = np.array(first)
b = np.array(second)
try:
    x = np.linalg.solve(a,b)
    print(x)
except Exception:
    print('ERROR: Cannot find solution.')