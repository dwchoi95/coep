def grade_stats(scores):
    first = scores[0]
    last = scores[-1]
    mean = round(sum(scores) / len(scores), 2)
    return [first, last, mean]
