a, b, c = map(int,input().split())
print("YES" if (a+b) == c or (b+c) == a or (c+a) == b else "NO")