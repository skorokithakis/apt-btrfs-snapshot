#!/usr/bin/python

import mock
import os
import sys
import unittest

sys.path.insert(0, "..")
sys.path.insert(0, ".")
import apt_btrfs_snapshot
from apt_btrfs_snapshot import (AptBtrfsSnapshot,
                                LowLevelCommands)

class TestFstab(unittest.TestCase):

    def test_fstab_detect_snapshot(self):
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab")
        self.assertTrue(apt_btrfs.snapshots_supported())
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab.no-btrfs")
        self.assertFalse(apt_btrfs.snapshots_supported())

    def test_fstab_get_uuid(self):
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab")
        self.assertEqual(apt_btrfs._uuid_for_mountpoint("/"),
                         "UUID=fe63f598-1906-478e-acc7-f74740e78d1f")

    @mock.patch('apt_btrfs_snapshot.LowLevelCommands')
    def test_mount_btrfs_root_volume(self, mock_commands):
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab")
        mock_commands.mount.return_value = True
        mock_commands.umount.return_value = True
        mp = apt_btrfs.mount_btrfs_root_volume()
        self.assertTrue("apt-btrfs-snapshot-mp-" in mp)
        self.assertTrue(apt_btrfs.umount_btrfs_root_volume())
        self.assertFalse(os.path.exists(mp))

    @mock.patch('apt_btrfs_snapshot.LowLevelCommands')
    def test_btrfs_create_snapshot(self, mock_commands):
        # setup mock
        mock_commands.btrfs_subvolume_snapshot.return_value = True
        mock_commands.mount.return_value = True
        mock_commands.umount.return_value = True
        # do it
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab")
        res = apt_btrfs.create_btrfs_root_snapshot()
        # check results
        self.assertTrue(apt_btrfs.commands.mount.called)
        self.assertTrue(apt_btrfs.commands.umount.called)
        self.assertTrue(res)
        self.assertTrue(apt_btrfs.commands.btrfs_subvolume_snapshot.called)
        (args, kwargs) = apt_btrfs.commands.btrfs_subvolume_snapshot.call_args
        self.assertTrue(len(args), 2)
        self.assertTrue(args[0].endswith("@"))
        self.assertTrue("@apt-snapshot-" in args[1])
        # again with a additional prefix for the snapshot
        res = apt_btrfs.create_btrfs_root_snapshot("release-upgrade-natty-")
        (args, kwargs) = apt_btrfs.commands.btrfs_subvolume_snapshot.call_args
        self.assertTrue("@apt-snapshot-release-upgrade-natty-" in args[1])

    @mock.patch('apt_btrfs_snapshot.LowLevelCommands')
    def test_btrfs_delete_snapshot(self, mock_commands):
        # setup mock
        mock_commands.btrfs_delete_snapshot.return_value = True
        mock_commands.mount.return_value = True
        mock_commands.umount.return_value = True
        # do it
        apt_btrfs = AptBtrfsSnapshot(fstab="./test/data/fstab")
        res = apt_btrfs.delete_snapshot("lala")
        self.assertTrue(res)
        self.assertTrue(apt_btrfs.commands.mount.called)
        self.assertTrue(apt_btrfs.commands.umount.called)
        self.assertTrue(apt_btrfs.commands.btrfs_delete_snapshot.called)
        (args, kwargs) = apt_btrfs.commands.btrfs_delete_snapshot.call_args
        self.assertTrue(args[0].endswith("/lala"))


if __name__ == "__main__":
    unittest.main()
