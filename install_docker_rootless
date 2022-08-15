#! /usr/bin/bash


# Run with sudo permissions
# Script made 4 Ubuntu, tested with 22.04

# Assuming you're installing docker under /home/<your-user> 
# You can change the directory later

sudo apt update
sudo apt install uidmap dbus-user-session

if [[ $(sudo systemctl status docker.service) -ne 0 ]]; then
  sudo systemctl disable --now docker.service docker.socket
fi

export PATH=/home/$(whoami)/bin:$PATH
export DOCKER_HOST=unix:///run/user/1000/docker.sock

sudo loginctl enable-linger 

export XDG_RUNTIME_DIR=/run/usr/$UID

systemctl --user start docker

systemctl --user enable docker
