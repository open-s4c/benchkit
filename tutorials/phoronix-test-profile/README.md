# Tutorial: Phoronix test profiles

## Clone the Phoronix test profiles repository

> **_Note:_** You can also create your own test profile.

```bash
cd tutorials/phoronix-test-profile/
git clone https://github.com/phoronix-test-suite/test-profiles.git
cd ..
```

## Generate venv & configure it

```bash
cd tutorials/phoronix-test-profile/
./configure.sh
cd ../..
```

## Choose what test profile to run

PhoronixTestProfileBench takes a `test_profile_src_dir` argument from which it runs the test profile, and which should contain the necessary files.
This can be changed from the example in [./campaign_phoronix_test_suite.py](./campaign_phoronix_test_suite.py).
