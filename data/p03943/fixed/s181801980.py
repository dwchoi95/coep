na = lambda: list(map(int, input().split()))
a, b, c = na()
if a + b == c or b + c == a or c + a == b:
    print("Yes")
else:
    print("No")