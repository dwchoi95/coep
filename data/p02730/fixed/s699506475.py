s=input()

def judge_palindrome(x):
	if x==x[::-1]:
		return True
	else:
		return False

if judge_palindrome(s)==True and judge_palindrome(s[:int((len(s)-1)/2)])==True and judge_palindrome(s[int((len(s)+3)/2)-1:])==True:
	print('Yes')
else:
	print('No')