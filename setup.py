"""
Setup script for the TCP/IP Network Simulator.
"""

from setuptools import setup, find_packages

setup(
    name="tcp_ip_simulator",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'tcp_ip_simulator=TCP_IP.main:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A modular TCP/IP Network Simulator focusing on the Physical and Data Link Layers",
    keywords="network, simulator, tcp/ip, datalink, physical",
    url="https://github.com/yourusername/tcp_ip_simulator",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Education",
        "Topic :: System :: Networking",
    ],
) 