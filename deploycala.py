#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2015, Teo Mrnjavac <teo@kde.org>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import sys
import shutil


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#following from Python cookbook, #475186
def has_colours(stream):
    if not hasattr(stream, "isatty"):
        return False
    if not stream.isatty():
        return False # auto color only on TTYs
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 2
    except:
        # guess false in case of error
        return False


has_colours = has_colours(sys.stdout)


def printout(text, colour=WHITE):
    if has_colours:
        seq = "\x1b[1;%dm" % (30+colour) + text + "\x1b[0m"
        return seq
    else:
        return text


def message(msg):
    sys.stdout.write(printout("==> ", GREEN) + printout(msg, WHITE) + "\n")


def bail(msg):
    sys.stdout.write(printout("==> ", RED) + printout("Fatal error: " + msg + "\n", WHITE))
    sys.exit(1)


def update_self():
    message("Updating deployment script...")
    thisfile = os.path.realpath(__file__)
    os.system("curl -o " + thisfile + " -L https://calamares.io/deploycala.py")
    os.system("chmod +x " + thisfile)

    myargs = sys.argv[:]
    message('Update complete, restarting %s' % ' '.join(myargs))

    myargs.insert(0, sys.executable)
    myargs.append('--noupdate')

    os.execv(sys.executable, myargs)


def yaourt_update(noupgrade):
    packages = ["cmake", "extra-cmake-modules", "boost"]
    if noupgrade:
        os.system("yaourt -Sy --noconfirm --needed " + " ".join(packages))
    else:
        os.system("yaourt -Syu --noconfirm --needed " + " ".join(packages))


def pacman_update(noupgrade):
    packages = ["cmake", "extra-cmake-modules", "boost"]
    if noupgrade:
        os.system("sudo pacman -Sy --noconfirm --needed " + " ".join(packages))
    else:
        os.system("sudo pacman -Syu --noconfirm --needed " + " ".join(packages))


# Courtesy of phihag on Stack Overflow,
# http://stackoverflow.com/questions/1006289/how-to-find-out-the-number-of-cpus-using-python
def available_cpu_count():
    # Python 3.4+
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        pass

    # POSIX
    try:
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))

        if res > 0:
            return res
    except (AttributeError, ValueError):
        pass

    # Linux
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')

        if res > 0:
            return res
    except IOError:
        pass

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", nargs="?", default="master",
                        help="the branch to checkout and build")
    parser.add_argument("-n", "--noupgrade", action="store_true", dest="noupgrade",
                        help="do not upgrade all the packages on the system before building")
    parser.add_argument("--noupdate", action="store_true", dest="noupdate", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not args.noupdate:
        update_self()

    cwd = os.getcwd()

    message("Backing up Calamares configuration and resources...")
    if os.path.isdir("/usr/share/calamares.backup"):
        os.system("sudo rm -rf /usr/share/calamares.backup")
    os.system("sudo cp -R /usr/share/calamares /usr/share/calamares.backup")
    if os.path.isdir("/etc/calamares.backup"):
        os.system("sudo rm -rf /etc/calamares.backup")
    os.system("sudo cp -R /etc/calamares /etc/calamares.backup")

    message("Updating build dependencies...")
    if shutil.which("yaourt"):
        yaourt_update(args.noupgrade)
    elif shutil.which("pacman"):
        pacman_update(args.noupgrade)
    else:
        bail("no package manager found.")

    branch = args.branch;
    if not branch:
        branch = "master"

    if os.path.isdir("calamares"):
        message("Clone found, checking out " + branch + " branch...")
        os.chdir("calamares")
        os.system("git checkout --track origin/" + branch + " -b " + branch)
        os.system("git pull --rebase")
        os.system("git submodule update")
        os.system("git submodule sync")
        if os.path.isdir("build"):
            shutil.rmtree("build", ignore_errors=True)
    else:
        message("Cloning and checking out " + branch + " branch...")
        os.system("git clone https://github.com/calamares/calamares.git")
        os.chdir("calamares")
        os.system("git checkout --track origin/"+ branch +" -b " + branch)
        os.system("git submodule init")
        os.system("git submodule update")
        os.system("git submodule sync")

    os.mkdir("build")
    os.chdir("build")
    cpu_count = available_cpu_count()
    if not cpu_count > 0:
        cpu_count = 4

    message("Found " + str(cpu_count) + " CPU cores, building...")
    os.system("cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=/usr -DWITH_PARTITIONMANAGER=1 .. && " +
              "make -j" + str(cpu_count) + " && " +
              "sudo make install")
    os.chdir(cwd)

    message("Restoring Calamares configuration and resources...")
    os.system("sudo cp -R /usr/share/calamares.backup/* /usr/share/calamares/")
    os.system("sudo cp -R /etc/calamares.backup/* /etc/calamares/")

    message("All done.")


if __name__ == "__main__":
    sys.exit(main())

