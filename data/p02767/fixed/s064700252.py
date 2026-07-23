from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

n = int(input())
x = list(map(int, input().split()))

ave = sum(x) / len(x)
p = Decimal(str(ave)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
squared = sum([i*i for i in x])

print(n*p*p - 2*p*sum(x) + squared)