import subprocess as sp

from multiprocessing import Pool

import os.path as osp

from ..utils import get_config_template, get_binary, seed_stream, PACKAGE_ROOT

from string import Template

from itertools import izip, repeat

import tempfile

__all__ = [
  'sim_worker',
  'SimStream'
]

def sim_worker(args):
  config, working_dir, seed, template = args

  workspace = tempfile.mkdtemp(dir=working_dir)

  if template is None:
    template = get_config_template()

  config_path = osp.abspath(osp.join(workspace, 'run.mac'))
  output_path = osp.abspath(osp.join(workspace, 'output.root'))

  config = config.copy()
  config['output'] = output_path
  config['seed1'] = seed[0]
  config['seed2'] = seed[1]

  with open(config_path, 'w') as f:
    f.write(
      Template(template).safe_substitute(**config)
    )

  process = sp.Popen(
    args=[get_binary(), config_path],
    cwd=PACKAGE_ROOT,
    stdin=sp.PIPE,
    stdout=sp.PIPE,
    stderr=sp.PIPE
  )

  stdout, stderr = process.communicate()
  retcode = process.wait()

  if retcode == 0:
    return config, stdout, stderr, workspace, output_path
  else:
    return config, stdout, stderr, workspace, None

def default_copy(target_dir, config, stdout, stderr):
  import shutil as sh
  import json

  config = config.copy()
  origin = config.pop('output', None)
  try:
    extension = origin.split('.')[-1]
  except:
    extension = ''

  props = sorted([ (k, v) for k, v in config.items() ], key=lambda x: x[0])
  name = '_'.join([ '%s=%s' % (k, v) for k, v in props ])
  target_path = osp.join(target_dir, name) + extension

  try:
    sh.move(origin, target_path)
  except Exception as e:
    import warnings
    warnings.warn(e.message)

  with open(target_path + '.json', 'w') as f:
    json.dump(config, f)

  with open(target_path + '.stdout', 'w') as f:
    f.write(stdout)

  with open(target_path + '.stderr', 'w') as f:
    f.write(stderr)

  return target_path

class SimStream(object):
  def __init__(self, target_dir, configs, super_seed, copy_op=default_copy, num_workers=1):
    self.template = get_config_template()
    self.work_dir = tempfile.mkdtemp(prefix='craysim')

    self.seed_stream = seed_stream(super_seed)
    self.pool = Pool(num_workers, maxtasksperchild=1)

    config_stream = izip(
      configs, repeat(self.work_dir), self.seed_stream, self.template
    )

    self.result_stream = self.pool.imap(sim_worker, config_stream, chunksize=1)
    self.copy_op = copy_op
    self.target_dir = target_dir

  def stream(self):
    for config, stdout, stderr, workspace, output_path in self.result_stream:
      try:
        yield self.copy_op(self.target_dir, config, stdout, stderr)
      except Exception as e:
        import warnings
        warnings.warn(e.message)
        warnings.warn(str(config))

