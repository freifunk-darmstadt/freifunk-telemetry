from setuptools import setup

setup(
    name='freifunk-telemetry',
    version='0.0.1',
    install_requires=[
        'psutil',
        'isc-dhcp-filter'
    ],
    packages=['freifunk_telemetry'],
    entry_points={
        'console_scripts': {
            'freifunk-telemetry = freifunk_telemetry:main'
        }
    }
)
