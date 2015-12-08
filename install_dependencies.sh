#!/bin/bash

# TODO : instead of chown, use 'su -'.
#        export TUTU=a ; su -  fritz -m -c 'echo "x=$TUTU"'
#
# TODO : check if debian based


# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi


function title() {
    echo "**************************************"
    echo "* $1"
    echo "**************************************"
}

function raise_error() {
    if [[ $1 -ne 0 ]] ; then
        echo "ERROR detected. Error code is : '$1'"
        exit 1
    fi
}


#####################################################################
# Domogik related informations
#####################################################################

title "Get the Domogik user..."
DOMOGIK_USER=$(grep DOMOGIK_USER /etc/default/domogik | cut -d"=" -f2)
if [[ "X"$DOMOGIK_USER == "X" ]] ; then
    echo "It seems that no Domogik is installed on your system!"
    exit 1
fi
echo "Domogik user is : $DOMOGIK_USER"
echo "Done"


#####################################################################
# pip and apt dependencies
#####################################################################

title "Install tailer with pip..."
pip install tailer
raise_error $?
echo "Done"

title "Install libudev-dev..."
apt-get install libudev-dev
# TODO : uncomment #    raise_error $?
echo "Done"


#####################################################################
# python-openzwave
#####################################################################

export PYOZW=python-openzwave-0.3.0b5
export DEP_DIR=./dependencies
export TMP_DIR=/tmp

### copy the tgz in /tmp and extract it

export SRC=$DEP_DIR/$PYOZW.tgz
export TARGET=$TMP_DIR/$PYOZW.tgz

title "Copy '$SRC' as '$TARGET'..."
cp $SRC $TARGET
raise_error $?
chown -R $DOMOGIK_USER $TARGET
raise_error $?
echo "Done"


title "Extract '$TARGET' in '$TMP_DIR/$PYOZW' ..."
cd $TMP_DIR 
tar xzf $PYOZW.tgz
raise_error $?
chown -R $DOMOGIK_USER $TMP_DIR/$PYOZW
raise_error $?
cd $TMP_DIR/$PYOZW
echo "Done"

### Install dependencies

title "Install the dependencies..."
#TODO : uncomment #   make deps
#TODO : uncomment #   raise_error $?
echo "Done"

### Build process

title "Build python-openzwave..."
echo "make clean..."
su $DOMOGIK_USER -c "make clean"
echo "make build..."
su $DOMOGIK_USER -c "make build"
