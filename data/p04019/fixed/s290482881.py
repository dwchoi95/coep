s = input()
l = len(s)
judge = 0
if 'N' in s:
    judge += 1000
if 'W' in s:
    judge += 1
if 'S' in s:
    judge -= 1000
if 'E' in s:
    judge -= 1

print('Yes' if judge == 0 else 'No')