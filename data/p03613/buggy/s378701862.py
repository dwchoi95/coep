

import copy
import sys
import math

n = int(input())
tmp = input().split()
hoge = list(map(lambda a: int(a), tmp))

hoge.sort()
hoge.append(0)
a=0
b=0
c=1
maxhoge=0
for i in range(0,n):
	maxhoge=max(maxhoge,a+b+c)
	if(hoge[i]!=hoge[i+1]):
		a=b
		b=c
		c=1
	else:
		c+=1




print(maxhoge)

