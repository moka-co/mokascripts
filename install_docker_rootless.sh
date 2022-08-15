#! /usr/bin/bash

# Run with sudo permissions
# Script made 4 Ubuntu, tested with 22.04

# Assuming you're installing docker under /home/<your-user> 
# This script doesn't work if you don't login with ssh as `ssh username@hostname`
# You can change the directory later

sudo apt update
sudo apt install uidmap dbus-user-session fuse-overlayfs -y

sudo -l > /dev/null

sudo loginctl enable-linger $(whoami)

echo "####" >> .profile
echo "export PATH=/home/$(whoami)/bin:\$PATH" >> .profile
echo "export DOCKER_HOST=unix:///run/user/1000/docker.sock" >> .profile
echo "export XDG_RUNTIME_DIR=/run/user/\$UID" >> .profile

source .profile

curl -fsSL https://get.docker.com/rootless | bash

systemctl --user daemon-reload
systemctl --user start docker && docker run hello-world

