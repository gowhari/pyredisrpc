import re
import os
from setuptools import setup


package_name = 'pyredisrpc'


def find_version():
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, package_name, '__init__.py')
    with open(path) as f:
        content = f.read()
    ver = re.findall('__version__ = (.+)', content)
    if not ver:
        raise RuntimeError('unable to find version string')
    ver = ver[0][1:-1]
    return ver


setup(
    name=package_name,
    version=find_version(),
    description='rpc over redis for python',
    long_description=open('README.rst').read(),
    long_description_content_type='text/x-rst',
    url='https://github.com/gowhari/pyredisrpc',
    author='Iman Gowhari',
    author_email='gowhari@gmail.com',
    license='MIT',
    packages=['pyredisrpc'],
    install_requires=['redis'],
    zip_safe=False,
)
