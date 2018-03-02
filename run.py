import os
import sys

import subprocess

if __name__ == '__main__':
  print(sys.argv)
  target = int(sys.argv[1])
  for item in os.listdir('./configs'):
    path = os.path.join('./configs', item)
    i = int(item.split('_')[0])
    if i == target:
      retcode = subprocess.call(['./bin/TestEm1', path])
      sys.exit(retcode)
