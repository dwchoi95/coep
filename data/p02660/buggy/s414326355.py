def resolve():
	import math
	N = int(input())
	if N==1:
		print(0)
	else:
		
		lst_e = []
		for p in range(2, math.ceil(math.sqrt(N))):
			e = 0
			while (N % p == 0):
				N /= p
				e += 1
			if e>0:
				lst_e.append(e)
		
		
		answer = 0
		for e in lst_e:
			i = 1
			while e >= i:
				e -= i
				i += 1
				answer += 1
		if answer == 0:
			answer = 1
		print(answer)
        
resolve()