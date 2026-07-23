s = input()
step = int(input())
print(''.join([s[i] for i in range(0, len(s), step)]))