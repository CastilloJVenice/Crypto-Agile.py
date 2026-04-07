# Crypto-Agile MVP - Run Instructions

## 1. Create virtualenv (recommended)
python -m venv venv
source venv/bin/activate  # linux / mac
venv\Scripts\activate     # windows

## 2. Install requirements
pip install -r requirements.txt

Note: If `pyoqs` installation fails, install it using your OS package manager or wheel. See https://github.com/open-quantum-safe/liboqs for help.

## 3. Run
python main.py

This will perform the test cases (iot, mobile, desktop, server), print results and write `results.csv`.

## 4. Expected outputs
- printed metrics per client case
- results.csv with chosen suite and measurement summary
