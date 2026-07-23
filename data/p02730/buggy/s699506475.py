s=input()

def judge_palindrome(x):
	
	flag=True
	if len(x)%2==0:
		flag=False
	for i in range(int((len(x)-1)/2)):
		if x[i]!=x[len(x)-1-i]:
			flag=False
	if flag:
		return True
	else:
		return False

if judge_palindrome(s) and judge_palindrome(s[:int((len(s)-1)/2)]) and judge_palindrome(s[int((len(s)+3)/2):]):
	print('Yes')
else:
	print('No')