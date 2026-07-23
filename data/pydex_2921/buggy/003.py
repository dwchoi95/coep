# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
from scipy import linalg
import numpy as np
first = map(float, input())
second = map(float, (input())
a = np.array(first)
b = np.array(second)
x = linalg.solve(a,b)
print(x)