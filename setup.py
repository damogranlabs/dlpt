import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dlpt",
    version="2.1.0",
    author="Damogran Labs",
    author_email="info@damogranlabs.com",
    description="Damogran Labs Python Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/damogranlabs/dlpt",
    project_urls={
        "Documentation": "https://dlpt.readthedocs.io/en/latest/",
    },
    packages=["dlpt"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["jsonpickle", "psutil"],
)
