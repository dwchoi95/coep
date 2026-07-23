s = input()
w = int(input())

length = len(s)

output = s[0]
i = w

while(i<length):
    output += s[w]
    i += w

print(output)
