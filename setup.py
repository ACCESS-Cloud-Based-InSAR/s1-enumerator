from pathlib import Path

from setuptools import find_packages, setup

readme = Path(__file__).parent / 'README.md'

setup(
    name='s1-enumerator',
    use_scm_version=True,
    description='Enumerates Sentinel-1 A/B Interferograms',
    long_description=readme.read_text(),
    long_description_content_type='text/markdown',

    url='https://github.com/ACCESS-Cloud-Based-InSAR/s1-enumerator',
    project_urls={},
    author='ACCESS Team',
    author_email='charlie.z.marshak@jpl.nasa.gov',
    license='Apache 2.0',
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='~=3.8',
    install_requires=[
        'geopandas', 'rasterio',
    ],

    extras_require={
        'develop': [
            'flake8',
            'flake8-import-order',
            'flake8-blind-except',
            'flake8-builtins',
            'pytest',
            'pytest-cov',
        ]
    },
    packages=find_packages(),
    zip_safe=False,
)
