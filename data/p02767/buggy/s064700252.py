from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

n = int(input())
x = list(map(int, input().split()))

x.sort()
ave = sum(x) / len(x)
squared = sum([i*i for i in x])

print(Decimal(str(squared - n*(ave)*ave)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))

