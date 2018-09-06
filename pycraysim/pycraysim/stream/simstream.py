import subprocess as sp

from multiprocessing import Pool

import os
import os.path as osp

from ..utils import get_config_template, get_binary, seed_stream, PACKAGE_ROOT

from string import Template

from itertools import izip, repeat

import tempfile

__all__ = [
  'sim_job',
  'sim_worker',
  'SimStream'
]

def sim_worker(args):
  config, working_dir, seed, template = args

  workspace = tempfile.mkdtemp(dir=working_dir)

  if template is None:
    template = get_config_template()

  config_path = osp.abspath(osp.join(workspace, 'run.mac'))
  output_path = osp.abspath(osp.join(workspace, 'output'))

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
    return config, stdout, stderr, workspace, output_path + '.root'
  else:
    return config, stdout, stderr, workspace, None

def naming(config):
  config = config.copy()

  config.pop('energyHisto', None)
  config.pop('output', None)

  props = sorted([(k, v) for k, v in config.items()], key=lambda x: x[0])
  name = '_'.join(['%s=%s' % (k, v) for k, v in props])
  return name + '.root'


def move(destination, config, stdout, stderr, retcode):
  import shutil as sh
  import json

  config = config.copy()
  origin = config['output'] + '.root'

  try:
    if retcode == 0:
      sh.move(origin, destination)
    else:
      raise Exception('Return code is not 0!')
  except:
    import traceback
    traceback.print_exc()

  with open(destination + '.json', 'w') as f:
    json.dump(config, f)

  with open(destination + '.stdout', 'w') as f:
    f.write(stdout)

  with open(destination + '.stderr', 'w') as f:
    f.write(stderr)

  return destination

def sim_job(config):
  config = config.copy()
  try:
    target_dir = config.pop('target')
    target_path = osp.join(target_dir, naming(config))

    if osp.exists(target_path):
      print('Output file already exists. Skipping.')
      return
  except:
    import traceback
    traceback.print_exc()
    return

  workspace = tempfile.mkdtemp(prefix='crayfis-sim')

  try:
    template = get_config_template()

    config_path = osp.abspath(osp.join(workspace, 'run.mac'))
    output_path = osp.abspath(osp.join(workspace, 'output'))

    config['output'] = output_path

    with open(config_path, 'w') as f:
      f.write(
        Template(template).substitute(**config)
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

    move(target_path, config, stdout, stderr, retcode)
  except:
    import traceback
    traceback.print_exc()
  finally:
    try:
      import shutil as sh
      sh.rmtree(workspace)
    except:
      import traceback
      traceback.print_exc()


class SimStream(object):
  def __init__(self, target_dir, configs, super_seed, copy_op=move, num_workers=1):
    self.template = get_config_template()
    self.work_dir = tempfile.mkdtemp(prefix='craysim')

    self.seed_stream = seed_stream(super_seed)
    self.pool = Pool(num_workers, maxtasksperchild=1)

    config_stream = izip(
      configs, repeat(self.work_dir), self.seed_stream, repeat(self.template)
    )

    self.result_stream = self.pool.imap(sim_worker, config_stream, chunksize=1)
    self.copy_op = copy_op
    self.target_dir = target_dir

  def stream(self):
    for config, stdout, stderr, workspace, output_path in self.result_stream:
      if output_path is None:
        raise Exception(stdout + '\n\n' + stderr)

      try:
        yield self.copy_op(self.target_dir, config, stdout, stderr)
      except Exception as e:
        import traceback
        import warnings

        warnings.warn(str(config))
        traceback.print_exc()

  def clean(self):
    import shutil as sh
    sh.rmtree(self.work_dir)