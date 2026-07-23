s = input()
if 'N' in s and 'W' in s and 'S' in s and 'E' in s:
    print('Yes')
elif ('N' in s and 'S' in s) and ('W' not in s and 'E' not in s):
    print('Yes')
elif ('N' not in s and 'S' not in s) and ('W' in s and 'E' in s):
    print('Yes')
else:
    print('No')