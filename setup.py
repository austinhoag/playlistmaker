from distutils.core import setup
setup(name='iTunes_custom_playlist',
      version='1.0',
      author='Austin Hoag',
      author_email='austinthomashoag@gmail.com',
      url='https://github.com/athoag/playlistmaker',
      packages=['playlistmaker'],
      package_dir = {'':'src'}
      )

# setup(name='Distutils',
#       version='1.0',
#       description='Python Distribution Utilities',
#       author='Greg Ward',
#       author_email='gward@python.net',
#       url='https://www.python.org/sigs/distutils-sig/',
#       packages=['distutils', 'distutils.command'],
#      )