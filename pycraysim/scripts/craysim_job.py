from pycraysim.stream import sim_job

if __name__ == '__main__':
  import sys
  args = sys.argv[1:]

  config = dict()

  for arg in args:
    tokens = arg.split('=')
    assert len(tokens) == 2, 'arguments should be in form <key>=<value>'

    k, v = tokens
    config[k] = v

    sim_job(config)