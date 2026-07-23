

import copy
import sys
import math

n = int(input())
tmp = input().split()
hoge = list(map(lambda a: int(a), tmp))

hoge.sort()
hoge.append(-1)
a=0
b=0
c=1
maxhoge=0
for i in range(0,n):
	if(hoge[i]!=hoge[i+1]):
		maxhoge=max(maxhoge,a+b+c)
		a=b
		b=c
		c=1
	else:
		c+=1




print(maxhoge)

