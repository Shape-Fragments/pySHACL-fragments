# pySHACL-fragments

Fork of [pySHACL](https://github.com/RDFLib/pySHACL) that adds shape fragment extraction to it (and breaks some other things).

## Requirements
- Python 3.6 or higher

## Installation
First, make a virtual environment, for example under `.venv`:
```bash
python3 -m venv .venv
```

Then, activate it and install pySHACL, which will install the required dependencies:
```bash
source .venv/bin/activate
pip3 install pyshacl
```

Then, to use the code in this repository over pySHACL's own code, add this repository to your python path (needs to be done for every new shell):
```bash
export PYTHONPATH=$(pwd)
```

## Usage
If not done already, activate your virtual environment and update your python path:
```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
```

To run pySHACL-fragments use:
```bash
python pyshacl/cli.py \
  -rs=True \
  <path-to-data-file> \
  -o <path-to-output-file> \
  -s <path-to-shape-file>
```