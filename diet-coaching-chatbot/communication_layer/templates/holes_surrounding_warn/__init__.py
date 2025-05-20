from datetime import datetime
import more_itertools as mit

def wordify(t):
    return f'{"{:%b %d}".format(t)}'

#TODO: handle shrinking in comparisons
def prepare_data(raw_data, compare):
    if len(raw_data) > 1:
        raw_data = [datetime.strptime(d, "%Y-%m-%d").toordinal() for d in raw_data]
        grouped = [list(group) for group in mit.consecutive_groups(raw_data)] #putting continous date-ranges in individual lists
        grouped = [[datetime.fromordinal(g[0]), datetime.fromordinal(g[-1])] if len(g)>1 else [g[0]] for g in grouped] #keeping only first and last day for each group
        grouped = [f'{wordify(g[0])}'+(f' - {wordify(g[-1])}' if len(g) > 1 else '') for g in grouped] #wordifying
    elif len(raw_data) > 0:
        grouped = [f'{wordify(datetime.strptime(raw_data[0], "%Y-%m-%d"))}']
    else:
        grouped = []

    return grouped
