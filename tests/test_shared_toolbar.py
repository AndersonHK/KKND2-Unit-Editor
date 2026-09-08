from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from support import editor, SOURCE, make_editor
from kknd2_editor.building_limits import LimitsConfig


class SharedToolbarTests(TestCase):
    def test_same_widgets_labels_and_positions_on_both_tabs(self):
        with TemporaryDirectory() as folder:
            app = make_editor(limits_path=Path(folder)/'building_limits.cfg', tk_scaling=96/72)
            try:
                for size in ('1500x1000', '850x900'):
                    app.geometry(size)
                    app.notebook.select(app.unit_page)
                    app.update()
                    def snapshot():
                        widgets = app.toolbar.buttons + list(app.notebook.bar.winfo_children())
                        return [(str(w), w.cget('text'), w.winfo_rootx(), w.winfo_rooty(),
                                 w.winfo_width(), w.winfo_height()) for w in widgets]
                    before = snapshot()
                    app.notebook.select(app.limits_page)
                    app.update()
                    self.assertEqual(snapshot(), before)
                    self.assertTrue(app.toolbar.winfo_ismapped())
                    self.assertTrue(app.limits_page.actions.winfo_ismapped())
                    self.assertGreater(app.limits_page.actions.winfo_rooty(), app.limits_page.panel.winfo_rooty())
                    for i, action in enumerate(('save', 'review', 'review_defaults', 'open_file', 'open_folder')):
                        with mock.patch.object(app.limits_page, action) as building_action, mock.patch.object(app, action) as unit_action:
                            app.toolbar.buttons[i].invoke()
                            building_action.assert_called_once()
                            unit_action.assert_not_called()
                    app.notebook.select(app.unit_page)
                    app.update()
                    self.assertEqual(snapshot(), before)
                    with mock.patch.object(app, 'save') as save:
                        app.toolbar.buttons[0].invoke()
                        save.assert_called_once()
            finally:
                app.destroy()

    def test_open_building_config_discard_and_save_target(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            first, second = folder/'first.cfg', folder/'second.cfg'
            doc = LimitsConfig(second)
            doc.apply(dict(doc.values, UNIT_SURV_TOWER1=9))
            doc.save()
            app = make_editor(limits_path=first)
            app.withdraw()
            try:
                page = app.limits_page
                page.variables['UNIT_SURV_TOWER1'].set('12')
                with mock.patch.object(editor.messagebox, 'askyesnocancel', return_value=None):
                    self.assertFalse(page.load_file(second))
                self.assertEqual(page.variables['UNIT_SURV_TOWER1'].get(), '12')
                with mock.patch.object(editor.messagebox, 'askyesnocancel', return_value=False):
                    self.assertTrue(page.load_file(second))
                self.assertEqual(page.variables['UNIT_SURV_TOWER1'].get(), '9')
                page.variables['UNIT_SURV_TOWER1'].set('10')
                self.assertTrue(page.save())
                self.assertEqual(LimitsConfig(second).values['UNIT_SURV_TOWER1'], 10)
                self.assertFalse(first.exists())
                page.variables['UNIT_SURV_TOWER1'].set('11')
                with mock.patch.object(editor.messagebox, 'askyesnocancel', return_value=False):
                    self.assertTrue(page.load_file(second))
                self.assertEqual(page.variables['UNIT_SURV_TOWER1'].get(), '10')
            finally:
                app.destroy()
