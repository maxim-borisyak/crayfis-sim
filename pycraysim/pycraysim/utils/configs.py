import os
import os.path as osp

import array
import numpy as np

particles = ['e-', 'e+', 'gamma', 'mu-', 'mu+', 'proton']

def get_package_root():
  path = osp.abspath(osp.dirname(__file__))

  for i in range(3):
   path = osp.split(path)[0]

  return path

PACKAGE_ROOT = get_package_root()

def seed_stream(super_seed):
  import random
  random.seed(super_seed)

  used_seeds= set()

  while True:
    seed = (random.randrange(int(1.0e+6)), random.randrange(int(1.0e+6)))

    if seed in used_seeds:
      continue
    else:
      used_seeds.add(seed)
      yield seed

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

def get_resource(paths, dir=True):
  resourse = osp.abspath(osp.join(PACKAGE_ROOT, *paths))

  assert osp.exists(resourse) and (osp.isdir if dir else osp.isfile)(resourse), \
    'resourse {what} [{where}] does not seem like a {what}'.format(
      where = resourse, what = 'directory' if dir else 'file'
    )

  return resourse

get_dir = lambda *paths: get_resource(paths, dir=True)
get_file = lambda *paths: get_resource(paths, dir=False)

get_config_path = lambda : get_file('config/run.mac.template')

def get_config_template(path='config/run.mac.template'):
  path = get_file(path)

  with open(path, 'r') as f:
    return f.read()

def get_spectrum(particle):
  import ROOT as r

  try:
    path = get_file('data/diff_spectra/', particle + '.dat')

    datfile = np.loadtxt(path)
  except Exception as e:
    datfile = np.loadtxt(particle)
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

def check_spectra(particles=particles):
  try:
    spectra_dir = get_dir('data', 'background_spectra')

    for particle in particles:
      if not osp.exists(osp.join(spectra_dir, particle + '.root')):
        return False

    return True
  except:
    return False

def generate_spectra(particles=particles):
  import ROOT as r

  data_dir = get_dir('data')
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

def get_priors(data_root=get_dir('data'), spectra_dir='background_spectra'):
  spectra_path = osp.join(data_root, spectra_dir)

  flux = dict()
  for particle in particles:
    particle_flux = get_total_flux(osp.join(spectra_path, particle + '.root'))
    flux[particle] = particle_flux

  total_flux = np.sum([ v for k, v in flux.values() ])

  return dict([
    (k, v / total_flux)
    for k, v in flux.items()
  ])

BINARY = 'TestEm1'

def get_binary():
  return get_file('bin', BINARY)

def generate_configs(output_dir, ngen=int(1.0e+5), pixWidth=1.5, pixDepth=(1, ), npix=5000, spectra_path=None, jobs=1):
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

  for job in range(jobs):
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

if __name__ == '__main__':
  import argparse
  import shutil as sh

  generate_spectra()

  parser = argparse.ArgumentParser(description='Generate configs for cosmic background simulation.')
  parser.add_argument('ngen', type=str, help='number of particles of each type to shoot')
  parser.add_argument('-o', '--output', default='./events/', type=str, help='simulation output directory')
  parser.add_argument('-w', '--pixWidth', default=1.5, type=float, help='pixel width')
  parser.add_argument('-n', '--npix', default=3000, type=int, help='linear size of the sensor')
  parser.add_argument('-r', '--runtime_spectra_path', default='data/background_spectra/', type=str, help='overrides path to spectra files')
  parser.add_argument('-s', '--super_seed', default=12345, type=int, help='seed to generate seeds')
  parser.add_argument('-j', '--jobs', default=1000, type=int, help='split simulation between number of jobs (per particle type)')
  parser.add_argument('-d', '--pixDepth', default=None, type=float, help='pixel depth (by default simulation enumerates a range of depths).')
  parser.add_argument('-c', '--configs_output', default='./configs/', type=str, help='output for the generated config files')

  args = parser.parse_args()

  try:
    os.makedirs(args.output)
  except OSError:
    pass

  with open(get_config_path(), 'r') as _f:
    from string import Template
    config = Template(_f.read())

  configs = list(generate_configs(
    output_dir = args.output,
    ngen = args.ngen,
    pixWidth = args.pixWidth,
    pixDepth=[args.pixDepth] if args.pixDepth is not None else None,
    npix = args.npix,
    jobs=args.jobs,
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

  for i, (name, values) in enumerate(configs):
    path = osp.join(args.configs_output, '%09d_%s.mac' % (i, name))

    with open(path, 'w') as f:
      f.write(config.substitute(values))
