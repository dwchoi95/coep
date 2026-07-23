def grade_stats(scores):
    return [min(scores), max(scores), round(2, sum(scores) / len(scores))]
