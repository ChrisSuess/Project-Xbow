sleep 30
sudo apt-get update
sudo apt-get install -y python3-pip nfs-common awscli zlib1g-dev
# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
sudo apt update
sudo apt install -y docker-ce
sudo usermod -aG docker ${USER}
# Install Task Spooler
sudo apt-get install -y task-spooler
# Install Xbowflow and Pinda
sudo pip3 install xbowflow
sudo pip3 install pinda
pinda update
mkdir -p $HOME/.local/bin
ln -s $HOME/.local/bin $HOME/bin
# Install Nvidia driver
sudo apt install -y nvidia-driver-430
# Install Nvidia container runtime for Docker
curl -s -L https://nvidia.github.io/nvidia-container-runtime/gpgkey | \
  sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list
sudo apt-get update
sudo apt-get install -y nvidia-container-runtime
sudo tee /etc/docker/daemon.json <<EOF
{
    "runtimes": {
        "nvidia": {
            "path": "/usr/bin/nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
EOF
sudo pkill -SIGHUP dockerd
# Install xbow-related services:
# These are a) the shared file system, b) the scheduler and c) the worker.
# Each can be activated independently by placing a particular file in
# the directory /run/metadata/xbow (which might need to be created).
# The expectation is that these files will be configured and installed as
# the instance is created/booted by passing a script as user data.
#
# a) A file called 'shared_file_system' containing a line of the form:
#      XBOW_SHARED_FILESYSTEM={fsid}.efs.{region}.amazonaws.com:/
#    will cause the shared file system to be mounted at /home/ubuntu/shared.
#
# b) A file called 'scheduler_ip_address' containg a line of the form:
#     XBOW_SCHEDULER_IP_ADDRESS=X.X.X.X
#    will cause a dask worker process to be started and pointed at a scheduler
#    that is assumed to exist at the given IP address.
#
# c) A file called 'is_scheduler' (which can be empty) will cause an xbow
#    scheduler to be started (as long as no file called 'scheduler_ip_address'
#    is also present, to avoid a single node starting both types of dask
#    service.
sudo mv /tmp/home-ubuntu-shared.path /etc/systemd/system
sudo mv /tmp/home-ubuntu-shared.mount /etc/systemd/system
sudo mv /tmp/xbow-scheduler.path /etc/systemd/system
sudo mv /tmp/xbow-worker.path /etc/systemd/system
sudo mv /tmp/xbow-scheduler.service /etc/systemd/system
sudo mv /tmp/xbow-worker.service /etc/systemd/system
# Ensure the "watchers" are launched on boot-up:
sudo systemctl enable home-ubuntu-shared.path
sudo systemctl enable xbow-scheduler.path
sudo systemctl enable xbow-worker.path
