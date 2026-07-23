import math

def prime(num):
	array=[]
	tmp=int(math.sqrt(n))+1
	for i in range(2,tmp):
		while num % i == 0:
			num/=i
			array.append(i)
	
	if array==[]:
		return [num]
	else:
		return array

n=int(input())
P=prime(n)
num=n
tmp=P[0]

if 1 in P:
	print(0)
else:	
	ans=1
	for i in range(1,len(P)):
		if P[i]==P[i-1]:
			tmp*=P[i]
		else:
			tmp=P[i]

		if num%tmp==0:
			num/=tmp
			ans+=1

	print(ans)