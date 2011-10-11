# Copyright (C) 2011 Canonical
#
# Author:
#  Michael Vogt
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import datetime
import os
import string
import subprocess
import sys
import time
import tempfile

class FstabEntry(object):
    """ a single fstab entry line """
    @classmethod
    def from_line(cls, line):
        return FstabEntry(*line.partition("#")[0].split())
    def __init__(self, fs_spec, mountpoint, fstype, options, dump=0, passno=0):
        # uuid or device
        self.fs_spec = fs_spec
        self.mountpoint = mountpoint
        self.fstype = fstype
        self.options = options
        self.dump = dump
        self.passno = passno
    def __repr__(self):
        return "<FstabEntry '%s' '%s' '%s' '%s' '%s' '%s'>" % (
            self.fs_spec, self.mountpoint, self.fstype,
            self.options, self.dump, self.passno)

class Fstab(list):
    """ a list of FstabEntry items """
    def __init__(self, fstab="/etc/fstab"):
        super(Fstab, self).__init__()
        for line in map(string.strip, open(fstab)):
            if line == "" or line.startswith("#"):
                continue
            try:
                entry = FstabEntry.from_line(line)
            except ValueError:
                continue
            self.append(entry)

class LowLevelCommands(object):
    """ lowlevel commands invoked to perform various tasks like
        inteact with mount and btrfs tools
    """
    def mount(self, fs_spec, mountpoint):
        ret = subprocess.call(["mount", fs_spec, mountpoint])
        return ret == 0
    def umount(self, mountpoint):
        ret = subprocess.call(["umount", mountpoint])
        return ret == 0
    def btrfs_subvolume_snapshot(self, source, dest):
        ret = subprocess.call(["btrfs", "subvolume", "snapshot",
                               source, dest])
        return ret == 0
    def btrfs_delete_snapshot(self, snapshot):
        ret = subprocess.call(["btrfs", "subvolume", "delete", snapshot])
        return ret == 0

class AptBtrfsSnapshot(object):
    """ the high level object that interacts with the snapshot system """
    
    # normal snapshot
    SNAP_PREFIX = "@apt-snapshot-"
    # backname when changing
    BACKUP_PREFIX = SNAP_PREFIX+"old-root-"
    
    def __init__(self, fstab="/etc/fstab"):
        self.fstab = Fstab(fstab)
        self.commands = LowLevelCommands()
        self._btrfs_root_mountpoint = None
    def snapshots_supported(self):
        """ verify that the system supports apt btrfs snapshots
            by checking if the right fs layout is used etc
        """
        # check for the helper binary
        if not os.path.exists("/sbin/btrfs"):
            return False
        # check the fstab
        for entry in self.fstab:
            if (entry.mountpoint == "/" and
                entry.fstype == "btrfs" and
                "subvol=@" in entry.options):
                return True
        return False
    def _uuid_for_mountpoint(self, mountpoint, fstab="/etc/fstab"):
        """ return the device or UUID for the given mountpoint """
        for entry in self.fstab:
            if entry.mountpoint == mountpoint:
                return entry.fs_spec
        return None
    def mount_btrfs_root_volume(self):
        uuid = self._uuid_for_mountpoint("/")
        mountpoint = tempfile.mkdtemp(prefix="apt-btrfs-snapshot-mp-")
        if not self.commands.mount(uuid, mountpoint):
            return None
        self._btrfs_root_mountpoint = mountpoint
        return self._btrfs_root_mountpoint
    def umount_btrfs_root_volume(self):
        res = self.commands.umount(self._btrfs_root_mountpoint)
        os.rmdir(self._btrfs_root_mountpoint)
        self._btrfs_root_mountpoint = None
        return res
    def _get_now_str(self):
        return  datetime.datetime.now().replace(microsecond=0).isoformat("_")
    def create_btrfs_root_snapshot(self, additional_prefix=""):
        mp = self.mount_btrfs_root_volume()
        snap_id = self._get_now_str()
        res = self.commands.btrfs_subvolume_snapshot(
            os.path.join(mp, "@"),
            os.path.join(mp, self.SNAP_PREFIX+additional_prefix+snap_id))
        self.umount_btrfs_root_volume()
        return res
    def get_btrfs_root_snapshots_list(self, older_than=0):
        """ get the list of available snapshot
            If "older_then" is given (in unixtime format) it will only include 
            snapshots that are older then the given date)
        """
        l = []
        if older_than == 0:
            older_than = time.time()
        mp = self.mount_btrfs_root_volume()
        for e in os.listdir(mp):
            if e.startswith(self.SNAP_PREFIX):
                # fstab is read when it was booted and when a snapshot is
                # created (to check if there is support for btrfs)
                atime = os.path.getatime(os.path.join(mp, e, "etc", "fstab"))
                if atime < older_than:
                    l.append(e)
        self.umount_btrfs_root_volume()
        return l
    def print_btrfs_root_snapshots(self):
        print "Available snapshots:"
        print "  \n".join(self.get_btrfs_root_snapshots_list())
        return True
    def _parse_older_than_to_unixtime(self, timefmt):
        now = time.time()
        if not timefmt.endswith("d"):
            raise Exception("Please specify time in days (e.g. 10d)")
        days = int(timefmt[:-1])
        return now - (days * 24 * 60 * 60)
    def print_btrfs_root_snapshots_older_than(self, timefmt):
        older_than_unixtime = self._parse_older_than_to_unixtime(timefmt)
        print "Available snapshots older than '%s':" % timefmt
        print "  \n".join(self.get_btrfs_root_snapshots_list(
                older_than=older_than_unixtime))
        return True
    def clean_btrfs_root_snapshots_older_than(self, timefmt):
        older_than_unixtime = self._parse_older_than_to_unixtime(timefmt)
        for snap in self.get_btrfs_root_snapshots_list(
            older_than=older_than_unixtime):
            self.delete_snapshot(snap)
    def command_set_default(self, snapshot_name):
        res = self.set_default(snapshot_name)
        print "Please reboot"
        return res
    def set_default(self, snapshot_name, backup=True):
        """ set new default """
        mp = self.mount_btrfs_root_volume()
        new_root = os.path.join(mp, snapshot_name)
        default_root = os.path.join(mp, "@")
        backup = os.path.join(mp, self.BACKUP_PREFIX+self._get_now_str())
        os.rename(default_root, backup)
        os.rename(new_root, default_root)
        self.umount_btrfs_root_volume()
        return True
    def delete_snapshot(self, snapshot_name):
        mp = self.mount_btrfs_root_volume()
        res = self.commands.btrfs_delete_snapshot(
            os.path.join(mp, snapshot_name))
        self.umount_btrfs_root_volume()
        return res
