# notes on building linux

## on Ubuntu

```
yes "" | make oldconfig
make menuconfig
make V=1 all
sudo make modules_install
sudo make install
```

## on openEuler

https://docs.openeuler.org/en/docs/21.03/docs/Installation/Installation.html

```
sudo yum makecache
sudo yum update
sudo yum install -y tmux vim git htop rsync hwloc-devel
sudo yum install -y ncurses-devel make gcc bc openssl-devel elfutils-libelf-devel rpm-build flex bison
```

```
wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.12.4.tar.xz
tar xvf linux-5.12.4.tar.xz
cd linux...
cp -v /boot/config-$(uname -r) .config
yes "" | make oldconfig
make menuconfig
    # -> suffix
    # CONFIG_DEBUG_INFO, CONFIG_SLUB_DEBUG and CONFIG_DEBUG_MISC to no
    # CONFIG_SYSTEM_TRUSTED_KEYS to ""
time make -j $(nproc)
sudo make modules_install
sudo make install
reboot
```
