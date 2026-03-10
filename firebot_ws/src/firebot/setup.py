import os
from glob import glob
from setuptools import setup

package_name = 'firebot'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Evan Schneider',
    maintainer_email='eschneider@sfsu.edu',
    description='FireBot ROS2 nodes',
    license='MIT',
    entry_points={
        'console_scripts': [
            'fire_detector_node = firebot.fire_detector_node:main',
            'brain_node = firebot.brain_node:main',
            'arduino_bridge_node = firebot.arduino_bridge_node:main',
            'sim_publisher = firebot.sim_publisher:main',
        ],
    },
)
