import heapq

mnum, gnum = map(int, input().split())
array = list(map(lambda a: -int(a), input().split()))

array.sort()
heapq.heapify(array)

for i in range(gnum):
	temp = heapq.heappop(array)
	temp = temp/2
	heapq.heappush(array, temp)
    
print(sum(array)*-1)