def resolve():
	answer = 0
	N = int(input())
	if N==1:
		print(answer)
	else:
		
		for p in range(2, int(N**0.5)+2):
			e = 0
			while (N % p == 0):
				N /= p
				e += 1
			
			if e>0:
				
				for i in range(1, e+1):
					if e >= i:
						e -= i
						answer += 1
		
		if N!=1:
			answer += 1
		print(answer)
        
resolve()