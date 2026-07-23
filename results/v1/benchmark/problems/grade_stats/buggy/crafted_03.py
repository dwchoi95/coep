def grade_stats(scores):
    lowest = min(scores)
    highest = max(scores)
    mean = round(sum(scores) / len(scores), 1)
    return [lowest, highest, mean]
