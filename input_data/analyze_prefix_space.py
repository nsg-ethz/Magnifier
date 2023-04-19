from collections import defaultdict


def get_prefixes(filename):
    prefixes = set()
    with open(filename, 'r') as data_in:
        for i, line in enumerate(data_in):
            cells = line.strip().split(',')
            prefixes.add(cells[2])

            if i % 100000000 == 0:
                print('done with', i)

    return prefixes


def analysis(filename):
    prefixes = get_prefixes(filename)
    counters = [0, 0, 0, 0]

    connected = defaultdict(int)
    void = defaultdict(int)

    length = 0
    continuous = False

    for a in range(256):
        for b in range(256):
            for c in range(256):
                prefix = '{}.{}.{}.0/24'.format(a, b, c)
                if prefix in prefixes:
                    if 0 <= a < 64:
                        counters[0] += 1
                    if 64 <= a < 128:
                        counters[1] += 1
                    if 128 <= a < 192:
                        counters[2] += 1
                    if 192 <= a < 256:
                        counters[3] += 1

                    if continuous:
                        length += 1
                    else:
                        void[length] += 1
                        continuous = True
                        length = 1

                else:
                    if not continuous:
                        length += 1
                    else:
                        connected[length] += 1
                        continuous = False
                        length = 1

    for key, value in void.items():
        print('void, len', key, 'amount', value)

    for key, value in connected.items():
        print('connected, len', key, 'amount', value)

    print('counters:', counters)


def save(filename):
    prefixes = get_prefixes(filename)
    with open('all_prefixes.txt', 'w') as data_out:
        for prefix in prefixes:
            data_out.write('{}\n'.format(prefix))


if __name__ == '__main__':
    analysis('simulation_input.csv')
