def grade_stats(scores):
    lo = scores[0]
    hi = scores[0]
    total = 0
    for s in scores:
        if s < lo:
            lo = s
        if s > hi:
            hi = s
        total += s
    return [lo, hi, round(2, total / len(scores))]
