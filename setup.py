from distutils.core import setup

setup(
    name="dewadl",
    version="0.1",
    description="Turn WADL descriptions into python APIs",
    author="Matt Kubilus",
    author_email="mattkubilus@gmail.com",
    packages=['dewadl'],
    package_dir={'dewadl':'.'},
    scripts=['dewadl.py']
)
