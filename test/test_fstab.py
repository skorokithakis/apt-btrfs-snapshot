#!/usr/bin/python

import mock
import os
import sys
import unittest

sys.path.insert(0, "..")
sys.path.insert(0, ".")
import apt_btrfs_snapshot
from apt_btrfs_snapshot import (AptBtrfsSnapshots,
                                Mount)

class TestFstab(unittest.TestCase):

    def test_fstab_detect_snapshot(self):
        apt_btrfs = AptBtrfsSnapshots(fstab="./test/data/fstab")
        self.assertTrue(apt_btrfs.snapshots_supported())
        apt_btrfs = AptBtrfsSnapshots(fstab="./test/data/fstab.no-btrfs")
        self.assertFalse(apt_btrfs.snapshots_supported())

    def test_fstab_get_uuid(self):
        apt_btrfs = AptBtrfsSnapshots(fstab="./test/data/fstab")
        self.assertEqual(apt_btrfs._uuid_for_mountpoint("/"),
                         "UUID=fe63f598-1906-478e-acc7-f74740e78d1f")

    @mock.patch('apt_btrfs_snapshot.Mount')
    def test_mount_btrfs_root_volume(self, mock_mount):
        apt_btrfs = AptBtrfsSnapshots(fstab="./test/data/fstab")
        mock_mount.mount.return_value = True
        mock_mount.umount.return_value = True
        mp = apt_btrfs.mount_btrfs_root_volume()
        self.assertTrue("apt-btrfs-snapshot-mp-" in mp)
        self.assertTrue(apt_btrfs.umount_btrfs_root_volume())
        self.assertFalse(os.path.exists(mp))

if __name__ == "__main__":
    unittest.main()
