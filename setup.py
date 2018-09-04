from setuptools import setup

setup(
    name='cffapp',
    packages=['cffapp'],
    include_package_data=True,
    install_requires=[
        'flask',
        'PyGitHub'
    ],
)
