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
	indices = defaultdict(lambda: [])
	Amax = NINF
	if 1 in indices:
		print(1 if len(indices[1]) == 1 else 0)
		return
	A.sort()	
	for i, num in enumerate(A):
		indices[num].append(i)
		Amax = max(Amax, num)
	set_false = set()
	dp = [1 for _ in range(n)]
	for i, num in enumerate(A):
		if i in set_false: continue
		if len(indices[num]) > 1:
			dp[i] = 0
		curr = num
		while curr <= Amax:
			for j in indices[curr]:
				if i == j: continue
				dp[j] = 0
				set_false.add(j)
			curr += num
	print(sum(dp))
	stdout.close()

if __name__ == "__main__":
	main()