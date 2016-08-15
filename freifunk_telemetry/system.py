def read_context_switches(update):
    with open('/proc/stat', 'r') as fh:
        for line in fh.readlines():
            key, value = line.split(' ', 1)
            if key == 'ctxt':
                update['context_switches'] = value.strip()
                break


def read_load(update):
    with open('/proc/loadavg', 'r') as fh:
        line = fh.read()
        values = line.split(' ', 3)
        update['load.15'] = values[0]
        update['load.5'] = values[1]
        update['load.1'] = values[2]
