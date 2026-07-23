


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
	ll = []
	for x,y in l:
		ll.append(x+y)
	return abs(min(ll) - max(ll))

N = int(stdin.readline())
L = []
for i in range(N):
	a,b = map(int, input().split())
	L.append([a,b])
ans = solve(L)
print(ans)

