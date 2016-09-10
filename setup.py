from setuptools import setup

setup(
    name='freifunk-telemetry',
    version='0.0.2',
    install_requires=[
        'psutil',
        'isc-dhcp-filter>=0.0.2',
        'pyroute2'
    ],
    packages=['freifunk_telemetry'],
    entry_points={
        'console_scripts': {
            'freifunk-telemetry = freifunk_telemetry:main'
        }
    }
)
