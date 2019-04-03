from setuptools import setup, find_packages

setup(
    name='galeranotify',
    author='Jan-Jonas Sämann',
    author_email='sprinterfreak@binary-kitchen.de',
    version='2.0',
    license='GPLv2',
    keywords='galeranotify mysql mariadb',
    description='A realtime email notifier for MySQL Galera-Cluster changes',
    url='https://git.binary-kitchen.de/sprinterfreak/galeranotify',
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Topic :: Database',
    ],
    packages=find_packages(),
    install_requires=[
        'PyYAML'
    ],
    entry_points={
        'console_scripts': {
            'galeranotify=galeranotify:main',
        },
    },
    data_files=[
        ('readme', ['README.md']),
        ('config', ['galeranotify.yml'])
    ],
)
