from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from support import editor, make_editor, SOURCE
from kknd2_editor import paths


class PortablePathsTests(TestCase):
    def test_frozen_settings_root_is_executable_folder(self):
        with TemporaryDirectory() as temporary:
            executable = Path(temporary)/'Editor folder'/'KKND2 Unit Editor.exe'
            with mock.patch.object(paths.sys, 'frozen', True, create=True), mock.patch.object(paths.sys, 'executable', str(executable)):
                self.assertEqual(paths.application_root(), executable.parent.resolve())

    def test_checkout_environment_and_selected_game_precedence(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second = root/'first game', root/'second game'
            for game in (first, second):
                (game/'UCONFIG').mkdir(parents=True)
            with mock.patch.object(paths, 'PROJECT_ROOT', first/'editor'), mock.patch.dict(paths.os.environ, {}, clear=True):
                self.assertEqual(paths.find_game_dir(), first.resolve())
                self.assertEqual(paths.default_limits_path(), first/'editor'/'building_limits.cfg')
                with mock.patch.dict(paths.os.environ, {'KKND2_GAME_DIR': str(second)}):
                    self.assertEqual(paths.find_game_dir(), second.resolve())
                    self.assertEqual(paths.find_game_dir(first/'UCONFIG'), first.resolve())
                self.assertEqual(paths.default_folder(second), second/'UCONFIG')
            with mock.patch.object(paths, 'PROJECT_ROOT', root/'standalone'), mock.patch.object(paths.Path, 'cwd', return_value=root), mock.patch.dict(paths.os.environ, {}, clear=True):
                self.assertIsNone(paths.find_game_dir())
                self.assertEqual(paths.default_folder(), root/'standalone'/'UCONFIG')

    def test_explicit_file_and_game_directory_without_installed_game(self):
        app = editor.Editor(initial=SOURCE, game_dir=SOURCE.parent,
                            limits_path=SOURCE.parent/'explicit-limits.cfg')
        try:
            self.assertEqual(app.path, SOURCE)
            self.assertEqual(app.folder, SOURCE.parent)
            self.assertEqual(app.game_dir, SOURCE.parent.resolve())
        finally:
            app.destroy()
