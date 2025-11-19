from setuptools import setup, find_packages

setup(
    name="flir-batch-extractor",
    version="0.1.0",
    description="Batch extractor for FLIR radiometric JPEGs, using FlirImageExtractor",
    author="jk, forked from ITVRoC",
    python_requires=">=3.8",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy",
        "Pillow",
        "matplotlib",
        "tqdm",
        "flirimageextractor",
    ],
    entry_points={
        "console_scripts": [
            "flir-batch-extractor = flir_batch_extractor:main",
        ],
    },
)

