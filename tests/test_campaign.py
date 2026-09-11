from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from support import synthetic_config
from kknd2_editor.campaign import command_line


class CampaignTests(TestCase):
    def test_native_display_name_and_quoted_command(self):
        with TemporaryDirectory(prefix='campaign test ') as temp:
            root=Path(temp);folder=root/'UCONFIG';folder.mkdir()
            path=folder/'UCONFIG_02.cfg';path.write_bytes(synthetic_config())
            exe=root/'KWIPv3.exe'
            self.assertTrue(command_line(exe,path).endswith('-stats "Test configuration"'))
            self.assertNotIn('-stats',command_line(exe))
            self.assertEqual(path.read_bytes(),synthetic_config())

    def test_ambiguous_and_unselectable_configurations_fail(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'UCONFIG';folder.mkdir()
            exe=root/'KWIPv3.exe';path=folder/'UCONFIG_02.cfg'
            path.write_bytes(synthetic_config())
            other=folder/'UCONFIG_03.cfg';other.write_bytes(synthetic_config())
            with self.assertRaisesRegex(ValueError,'share the title'):command_line(exe,path)
            other.unlink()
            for bad in (root/'UCONFIG_02.cfg',folder/'UCONFIG_30.cfg',folder/'custom.cfg'):
                with self.assertRaisesRegex(ValueError,'UCONFIG_00'):command_line(exe,bad)
            path.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'incomplete'):command_line(exe,path)
            path.write_bytes(bytes(120))
            with self.assertRaisesRegex(ValueError,'nonempty'):command_line(exe,path)
