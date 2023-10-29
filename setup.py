import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="protobuf_decoder",
    version="0.3.0",
    author="danny han",
    author_email="rhrnak0501@gmail.com",
    description="Decode protobuf without proto file",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dannyhann/protobuf_decoder",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
