#!/usr/bin/env python

from distutils.core import setup

setup(name='apt-btrfs-snapshot',
      version='0.1',
      author='Michael Vogt',
      url='http://launchpad.net/apt-btrfs-snapshot',
      scripts=['apt-btrfs-snapshot'],
      py_modules=['apt_btrfs_snapshot'],
      )
