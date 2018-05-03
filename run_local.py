import os
import os.path as osp

import ROOT as r

import array
import numpy as np

__all__ = [
  'generate_configs'
]

particles = ['e-', 'e+', 'gamma', 'mu-', 'mu+', 'proton']

def get_seeds(n, super_seed):
  import random
  random.seed(super_seed)

  numbers = []

  while len(set(numbers)) != n:
    numbers = [
      (random.randrange(int(1.0e+6)), random.randrange(int(1.0e+6)))
      for _ in range(n)
    ]

  return numbers

def get_resourse(path, dir=True):
  here = osp.dirname(osp.abspath(__file__))

  resourse = osp.abspath(osp.join(here, path))
  assert osp.exists(resourse) and (osp.isdir if dir else osp.isfile)(resourse), \
    'resourse {what} [{where}] does not seem like a {what}'.format(
      where = resourse, what = 'directory' if dir else 'file'
    )

  return resourse

get_dir = lambda path: get_resourse(path, dir=True)
get_file = lambda path: get_resourse(path, dir=False)

def get_spectrum(particle):
  import ROOT as r

  try:
    path = get_file(osp.join('./data/diff_spectra/', particle + '.dat'))
    datfile = np.loadtxt(path)
  except Exception as e:
    raise e

  ns = np.arange(datfile.shape[0] + 1)
  bins = 10.0 ** (ns / 10.0 - 2)
  assert np.allclose(datfile[:, 0], (bins[1:] + bins[:-1]) / 2.0, rtol=1.0e-2, atol=0.0)

  # ROOT is picky and wants python array.array for TH1F constructor
  binsx = array.array('d', bins)
  h = r.TH1F("energy", particle, len(binsx)-1, binsx)
  for i, rate in enumerate(datfile[:, 1]):
      h.Fill(
        (binsx[i] + binsx[i + 1]) / 2,
        rate * (binsx[i + 1] - binsx[i])
      )

  return h

def generate_spectra(particles=particles):
  import ROOT as r
  data_dir = get_dir('./data')
  spectra_dir = osp.join(data_dir, 'background_spectra')

  try:
    os.makedirs(spectra_dir)
  except:
    pass

  for particle in particles:
    f_out = r.TFile(osp.join(spectra_dir, particle + '.root'), 'RECREATE')
    h = get_spectrum(particle)
    h.Write()
    f_out.Close()

  return spectra_dir

def get_total_flux(path):
  import ROOT as r

  f = r.TFile(path)
  h = f.Get('energy')

  return np.sum([
    h.GetBinContent(i)
    for i in range(h.GetSize())
  ])


def generate_configs(output_dir, ngen, pixWidth, pixDepth, npix=5000, spectra_path=None, splits=1):
  print('Pixel depths: %s' % pixDepth)

  hist_dir = generate_spectra(particles=particles)
  hists = [
    osp.join(hist_dir, p + '.root')
    for p in particles
  ]

  fluxes = [ get_total_flux(hist) for hist in hists ]
  print("Total flux: %.3e" % np.sum(fluxes))
  print(
    "Fluxes:\n  %s" % '\n  '.join([
      "%s: %.3e MeV" % (particle, flux)
      for particle, flux in zip(particles, fluxes)
    ])
  )

  priors = [ flux / np.sum(fluxes) for flux in fluxes ]
  print(
    "Priors:\n  %s" % '\n  '.join([
      "%s: %.3e" % (particle, prior)
      for particle, prior in zip(particles, priors)
    ])
  )

  assert len(hists), 'there is no data for cosmic background spectra!'

  if spectra_path is None:
    spectra_path = hist_dir

  runtime_hists = [
    osp.join(spectra_path, osp.basename(hist))
    for hist in hists
  ]

  for job in range(splits):
    for depth in pixDepth:
      for particle, hist in zip(particles, runtime_hists):
        name = '{particle}_{job:06d}_depth={depth}'.format(particle=particle, job=job, depth=depth)
        config = dict(
          beamEnergy=-1,
          particle=particle,
          energyHisto=hist,
          ngen=ngen,
          pixDepth=depth,
          pixWidth=pixWidth,
          npix=npix,
          output=osp.join(output_dir, name)
        )

        yield name, config

def worker(args):
  from tempfile import NamedTemporaryFile
  from subprocess import Popen, PIPE
  import os

  template, (_, config) = args

  with NamedTemporaryFile(delete=False) as f:
    f.write(template.substitute(config))
    tmpf = f.name

  executable = get_file('./bin/TestEm1')

  proc = Popen([executable, tmpf], stdout=PIPE, stderr=PIPE)
  stdout, stderr = proc.communicate()
  retcode = proc.returncode

  os.remove(tmpf)

  return retcode, stdout, stderr

if __name__ == '__main__':
  import argparse

  generate_spectra()

  parser = argparse.ArgumentParser(description='Runs craysim')
  parser.add_argument('ngen', type=str, help='number of particles of each type to shoot')
  parser.add_argument('-o', '--output', default='./events/', type=str, help='simulation output directory')
  parser.add_argument('-w', '--pixWidth', default=1.5, type=float, help='pixel width')
  parser.add_argument('-n', '--npix', default=3000, type=int, help='linear size of the sensor')
  parser.add_argument('-r', '--runtime_spectra_path', default='data/background_spectra/', type=str, help='overrides path to spectra files')
  parser.add_argument('-s', '--super_seed', default=12345, type=int, help='seed to generate seeds')
  parser.add_argument('-t', '--tasks', default=1, type=int, help='number of task for each configuration')
  parser.add_argument('-d', '--pixDepth', nargs='+', type=float, help='pixel depth (by default simulation enumerates a range of depths).')
  parser.add_argument('-c', '--configs_output', default='./configs/', type=str, help='output for the generated config files')
  parser.add_argument('-j', '--jobs', default=1, type=int, help='number of parallel processes')


  args = parser.parse_args()

  try:
    os.makedirs(args.output)
  except OSError:
    pass

  with open(get_file('./data/config/run.mac.template'), 'r') as _f:
    from string import Template
    template = Template(_f.read())

  configs = list(generate_configs(
    output_dir = args.output,
    ngen = args.ngen,
    pixWidth = args.pixWidth,
    pixDepth=args.pixDepth,
    npix = args.npix,
    splits=args.tasks,
    spectra_path=args.runtime_spectra_path
  ))

  super_seed = args.super_seed

  for (_, values), (seed1, seed2) in zip(configs, get_seeds(len(configs), super_seed=super_seed)):
    values['seed1'] = seed1
    values['seed2'] = seed2

  try:
    os.makedirs(args.configs_output)
  except OSError:
    pass

  print('There are total %d tasks.' % len(configs))

  import tqdm
  tqdm.monitor_interval = 0

  from multiprocessing import Pool

  pool = Pool(processes=args.jobs)

  results = []

  for result in tqdm.tqdm(
    pool.imap(worker, zip([template] * len(configs), configs)),
    total=len(configs)
  ):
    results.append(result)

  for retcode, stdout, stderr in results:
    if retcode != 0:
      print('Return code: %d;\nstdout:\n%s\nstderr:\n%s\n' % (retcode, stdout, stderr))

  if all([ retcode == 0 for retcode, _, _ in results ]):
    print('All processes finished successfully!')