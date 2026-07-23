def grade_stats(scores):
    lowest = min(scores)
    highest = max(scores)
    mean = round(sum(scores) / len(scores))
    return [lowest, highest, mean]
