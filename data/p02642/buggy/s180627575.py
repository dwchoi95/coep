from sys import stdin, stdout, setrecursionlimit
from collections import deque, defaultdict, Counter
import math

rl = lambda: stdin.readline()
rll = lambda: stdin.readline().split()
rli = lambda: map(int, stdin.readline().split())
rlf = lambda: map(float, stdin.readline().split())

INF, NINF = float('inf'), float('-inf')

def main():
	n = int(rl())
	A = list(rli())
	Aset = set(A)
	if 1 in Aset:
		print(1)
		return
	Acnt = Counter(A)
	ans = 0
	for i, num in enumerate(A):
		div = 2
		flag = True
		if Acnt[num] > 1:
			continue
		while div*div <= num:
			if num % div == 0:
				other = num
				if div in Aset or other in Aset:
					flag = False
					break
			div += 1
		if flag:
			ans += 1
	print(ans)
	stdout.close()

if __name__ == "__main__":
	main()