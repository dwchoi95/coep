S = [1 if _ == 'p' else 0 for _ in input()]
N = len(S)
count_g = 0
count_p = 0
score = 0
for hand_t in S:
    if count_p < count_g:
        count_p += 1
        hand_a = 1
    else:
        count_g += 1
        hand_a = 0
    score += hand_a - hand_t

print(score)
