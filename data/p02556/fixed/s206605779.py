


from math import *
from copy import *                      
from heapq import *                     
from string import *                    
from random import *                    
from bisect import *                    
from sys import stdin                   
from sys import maxsize                 
from operator import *                  
from itertools import *                 
from decimal import Decimal             
from collections import Counter         
from collections import defaultdict     



def solve(l):
	n = len(l)
	d = defaultdict(int)
	l1,l2,l3 = [],[],[]
	for x,y in l:
		l1.append(x+y)
		l2.append(x-y)
		l3.append(y-x)
	a = abs(max(l1) - min(l1))
	b = abs(max(l2) - min(l2))
	c = abs(max(l3) - min(l3))
	return max(a,b,c)

N = int(stdin.readline())
L = []
for i in range(N):
	a,b = map(int, input().split())
	L.append([a,b])
ans = solve(L)
print(ans)

