from setuptools import setup

with open('README.md') as readme:
    readme_text = readme_file.read()

setup(
    use_scm_version=True,
    long_description=readme_text,
