#!/bin/sh

# assume that all other scripts are located in the same directory as this script
path=$(dirname $(readlink -f $0))

# These actions will be executed during login
$path/login-actions.sh

# This starts a listener for logout signalling and executes the actions during logout
$path/gendsession.py $path/logout-actions.sh
