s = input()
l = len(s)
judge = 0
if 'N' in s:
    judge += 2
if 'W' in s:
    judge += 1/1000
if 'S' in s:
    judge -= 2
if 'E' in s:
    judge -= 1/1000

print('Yes' if judge == 0 else 'No')