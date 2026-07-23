nums = input()
numi = int(nums)

sum = 0
for ds in nums:
    di = int(ds)
    sum += di ** 3

same = "the"
if (sum != numi):
    same = "NOT"

print ('Sum of Cubes is {}. It is {} same as the number {}.'.format(sum, same, nums))
    

