from distutils.core import setup
import sys
from imp import find_module

try: find_module('sqlalchemy')
except: sys.exit('### Error: python module sqlalchemy not found')

setup(name='iTunes_custom_playlist',
      version='1.0',
      author='Austin Hoag',
      author_email='austinthomashoag@gmail.com',
      url='https://github.com/athoag/playlistmaker',
      py_modules=['src/iTunes_custom_playlist']
      )