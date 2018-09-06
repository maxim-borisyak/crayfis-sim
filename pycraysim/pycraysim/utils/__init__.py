from .configs import *
from .args import *

if not check_spectra(particles):
  generate_spectra(particles)
