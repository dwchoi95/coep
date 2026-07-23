s = input()

p_count = 0
g_count = 0
win = 0

for i in list(s):
    if i == "g" and p_count + 1 <= g_count:
        p_count += 1
        win += 1
    elif i == "g":
        g_count += 1
    elif i == "p" and p_count + 1 <= g_count:
        p_count += 1
    else:
        g_count += 1
        win -= 1

print(win)
