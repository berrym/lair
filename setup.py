from setuptools import setup

setup(
    name="The Lair",
    version="0.1.1",
    packages=["lairchat", "lairchat.cli", "lairchat.gui", "lairchat.crypto"],
    url="https://github.com/berrym/lair",
    license="GPLv3",
    author="Michael Berry",
    author_email="trismegustis@gmail.com",
    description="A small and simple chat application written in Python 3 and Qt5.",
    install_requires=["PyQt5", "pycryptodomex"],
)
