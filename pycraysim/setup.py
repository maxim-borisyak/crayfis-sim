from setuptools import setup, find_packages

setup(
  name='craysim',

  version='0.1.1',

  description="""CRAYFIS simulation stream""",

  url='https://github.com/maxim-borisyak/crayfis-stream',

  author='Maxim Borisyak, Chase Shimmin',
  author_email='mborisyak at hse dot ru',

  maintainer = 'Maxim Borisyak, Chase Shimmin',
  maintainer_email = 'mborisyak at hse dot ru',

  license='MIT',

  classifiers=[
    'Development Status :: 4 - Beta',

    'Intended Audience :: Science/Research',

    'License :: OSI Approved :: MIT License',

    'Programming Language :: Python :: 3',
  ],

  keywords='',

  packages=find_packages(where='.', exclude=['contrib', 'examples', 'docs', 'tests']),

  extras_require={
    'dev': ['check-manifest'],
    'test': ['nose>=1.3.0'],
  },

  include_package_data=True,

  package_data = {
  },
)
