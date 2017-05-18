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

# Display a title
function title() {
    tput cols > /dev/null 2>&1
    if [[ $? -eq 0 ]] ; then
        # tput cols works, we generate dynamically the width
        printf '[xxxxxxx] %*s\n' "$(( ${COLUMNS:-$(tput cols)} - 10 ))" '' | tr ' ' - | tr 'x' ' '
        echo "[       ]        $*"
        printf '[xxxxxxx] %*s\n' "$(( ${COLUMNS:-$(tput cols)} - 10 ))" '' | tr ' ' - | tr 'x' ' '
    else
        # tput cols does not work (maybe this is run over ssh), we use 80 as width
        printf '[xxxxxxx] %*s\n' "70" '' | tr ' ' - | tr 'x' ' '
        echo "[       ]        $*"
        printf '[xxxxxxx] %*s\n' "70" '' | tr ' ' - | tr 'x' ' '
    fi
}

#info
# Display messages in yellow
function info() {
    echo -e "[ INFO  ] \e[93m$*\e[39m"
}

# prompt
# Display messages in blue
function prompt() {
    echo -e "[       ] \e[35m$*\e[39m"
}

# ok
# Display messages in green
function ok() {
    echo -e "[ OK    ] \e[92m$*\e[39m"
}

# error
# Display messages in red
function error() {
    #echo -e "[ ERROR ] \e[91m$*\e[39m"
    echo -e "[ \e[5mERROR\e[0m ] \e[91m$*\e[39m"
}

# abort
# display an error message and exit the installation script
function abort() {
    error $*
    echo -e "[ \e[5mABORT\e[0m ] \e[91mThe installation is aborted due to the previous error!\e[39m"
    exit 1
}

function raise_error() {
    if [[ $1 -ne 0 ]] ; then
        error $*
        continue
    fi
}

function continue() {
    prompt "Do you still want to continue ? [y/N]"
    read yesno
    yesno=$(echo $yesno | awk '{print tolower($0)}')
    case $yesno in
        "y") ok "continue" ;;
        "n") abort "exiting..." ;;
        *) continue;;
    esac
}

function check_debian_based() {
    distrib=$(lsb_release -si)
    if [[ $? -ne 0 ]] ; then
        error "lsb_release not installed or not working. This script needs lsb_release to check if you are using a compliant OS"
    fi
    if [[ "x$distrib" == "x" ]] ; then
        abort "Unknown Linux release. This script is dedicated to Debian based Linux releases"
    fi

    case $distrib in
        "Debian")     info "The linux release is : '$distrib'. OK" ;;
        "Ubuntu")     info "The linux release is : '$distrib'. OK" ;;
        "Raspbian")   info "The linux release is : '$distrib'. OK" ;;
        *)            error "Your Linux release '$distrib' is not compliant with this installation script. This script is dedicated to Debian based Linux releases" ; exit 1 ;;
    esac

}


#####################################################################
# Check if the OS is Debian based
#####################################################################

check_debian_based


#####################################################################
# Domogik related informations
#####################################################################

title "Get the Domogik user..."
DOMOGIK_USER=$(grep DOMOGIK_USER /etc/default/domogik | cut -d"=" -f2)
if [[ "X"$DOMOGIK_USER == "X" ]] ; then
    abort "It seems that no Domogik is installed on your system!"
fi
info "Domogik user is : $DOMOGIK_USER"
ok "Done"


#####################################################################
# pip and apt dependencies
#####################################################################

title "Install tailer with pip..."
pip install tailer
raise_error $?
ok "Done"

title "Install libudev-dev..."
apt-get install -y libudev-dev
raise_error $?
ok "Done"


#####################################################################
# python-openzwave
#####################################################################

export TMP_DIR=/tmp
python_openzwave_version=""
export VIRTUALENV=""

while :
do
    case "$1" in
      -LAST)
            title "Get last version of python-openzwave"
            if [[ $python_openzwave_version = "" ]]
                then
                    wget -N https://raw.githubusercontent.com/OpenZWave/python-openzwave/master/pyozw_version.py
                    if [[ $? != 0 ]]
                        then
                            abort ":( Can't get check version script."
                        else
                            python_openzwave_version=$(python pyozw_version.py)
                    fi
                    shift
                else
                    abort ":( Option number mess : "$python_openzwave_version" , check your option script"
            fi
            ;;
      -v)
            title "Get specific version of python-openzwave"
            if [[ $python_openzwave_version = "" ]]
                then
                    if [[ $2 =~ ^[0-9]+\.[0-9]+ ]]
                        then
                            python_openzwave_version=$2
                            ok $python_openzwave_version
                        else
                            abort ":( Bad version number format : "$2" , use N.N.N"
                    fi
                    shift 2
                else
                    abort ":( Option number mess : "$python_openzwave_version" , check your option script"
            fi
            ;;
      -env) # Must be at first
            title "Install python-openzwave lib in virtualenv : "$2
            export VIRTUALENV=$2
            shift 2
            ;;
      -pip)
            title "Install python-openzwave from pip"
            if [[ $VIRTUALENV != "" ]]
                then
                    info "make install-lib in virtual env ("$VIRTUALENV")"
                    source $VIRTUALENV/bin/activate
            fi
            apt-get install --force-yes -y make libudev-dev g++ libyaml-dev
			pip install python_openzwave
            raise_error $?
            ok "Done"
            exit 0
            ;;
      *)  # No more options
            if [[ $python_openzwave_version = "" ]]
                then
                    info "****** Get default version *****"
                    python_openzwave_version="0.3.3"
                    ok "Default : "$python_openzwave_version
            fi
            break
        ;;
    esac
done

export PYOZW=python-openzwave-${python_openzwave_version}
wget -N -P ${TMP_DIR}  https://raw.githubusercontent.com/OpenZWave/python-openzwave/master/archives/${PYOZW}.tgz
if [ $? -ne 0 ]
then
    abort ":( Can not get check archive file."
else
    title "Version "$python_openzwave_version" retreived"
fi

### extract the tgz in /tmp

export TARGET=$TMP_DIR/$PYOZW.tgz

chown -R $DOMOGIK_USER $TARGET
raise_error $?
ok "Done"

title "Extract '$TARGET' in '$TMP_DIR/$PYOZW' ..."
cd $TMP_DIR
tar xzf $PYOZW.tgz
raise_error $?
chown -R $DOMOGIK_USER $TMP_DIR/$PYOZW
raise_error $?
cd $TMP_DIR/$PYOZW
ok "Done"

### uninstall previous lib

title "Uninstall the previous python-openzwave lib..."
sudo make uninstall
raise_error $?
ok "Done"

### Install dependencies

title "Install the dependencies..."
make deps
raise_error $?
ok "Done"

### Build process

title "Build python-openzwave..."
info "make clean..."
sudo make clean
raise_error $?

info "make build..."
su $DOMOGIK_USER -c "make build"
raise_error $?

if [[ $VIRTUALENV != "" ]]
    then
        info "make install-lib in virtual env ("$VIRTUALENV")"
        sudo make PYTHON_EXEC=$VIRTUALENV"/bin/python" install-lib
    else
        info "make install-lib..."
        sudo make install-lib
fi
raise_error $?
