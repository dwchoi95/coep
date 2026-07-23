nums = input().split()

S = int(nums[0])
W = int(nums[1])


if (S < W ):
	print("unsafe")
else:
	print("safe")