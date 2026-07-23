a = [int(_) for _ in input().split()]
print('Yes' if a[0] == a[1] + a[2] else 'Yes' if a[1] == a[0] + a[2] else 'yes' if a[2] == a[0] + a[1] else 'No')