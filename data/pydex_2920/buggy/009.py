# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
### DO NOT CHANGE. REQUIRED TO PLOT IN PRUTOR #################################
import math
import prutorplotlib as pl
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
###############################################################################




# YOUR CODE GOES HERE ********************

V=int(input())
A=int(input())
g=9.8
Ar=math.radians(A)
T=2*V*math.sin(Ar)/g
x1=V*math.cos(Ar)*T
y1=(V*math.sin(Ar)T/2)+((-g/2)(T/2)**2)
print('Time of Flight =',float(round(T,2)))
print('Distance Covered =',float(round(x1,2)))
print('Peak Height =',float(round(y1,2)))


x = np.array(range(0,int(x1)))
k1=math.tan(Ar)
k2=g/(2*(V*math.cos(Ar))**2)
y = x*k1-(x**2)*k2


plt.plot(x,y)
plt.show()


### DO NOT CHANGE. REQUIRED TO PLOT IN PRUTOR #################################
pl.prutorsaveplot(plt, 'plot1.pdf')
###############################################################################