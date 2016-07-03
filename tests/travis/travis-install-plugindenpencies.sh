#!/bin/bash -e 
# The -e option will make the bash stop if any command raise an error ($? != 0)

echo "==== Install zwave emulator dependency"
sudo apt-get install socat
cd $TRAVIS_BUILD_DIR
git clone git@github.com:Nico0084/py-zwave-emulator.git
export ZWEMULATOR = py-zwave-emulator/bin/zwemulator.py
ls -l py-zwave-emulator/bin/

echo "==== Install Plugin dependency"
sudo ./tests/travis/travis-install-plugindenpencies.sh -LAST

echo "==== Start zwave emulator"
python $ZWEMULATOR &





