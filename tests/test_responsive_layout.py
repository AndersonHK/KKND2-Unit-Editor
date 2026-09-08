"""Preserve the original readable layout while resizing the new tabbed editor."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from tkinter import ttk
from support import editor, SOURCE, make_editor


class ResponsiveLayoutTests(TestCase):
    def test_old_alignment_and_columns_follow_each_resize(self):
        with TemporaryDirectory() as folder:
            for scaling in (1, 2):
                with self.subTest(dpi=scaling * 100):
                    app = make_editor(tk_scaling=96 / 72 * scaling,
                                        limits_path=Path(folder) / 'limits.cfg')
                    try:
                        app.update()
                        labels = [w for w in app.stats.content.winfo_children()
                                  if int(w.grid_info().get('column', -1)) == 0
                                  and int(w.grid_info().get('row', 0)) > 0]
                        self.assertEqual(len(labels), 17)
                        for label in labels:
                            self.assertIsInstance(label, ttk.Label)
                            self.assertEqual(str(label.cget('justify')), 'left')
                            self.assertIn('\n', label.cget('text'))
                            self.assertEqual(label.grid_info()['sticky'], 'w')
                            self.assertEqual(label.grid_info()['pady'], app.px(7))

                        natural = app.stats.content.winfo_reqwidth()
                        previous_width = previous_saved_x = None
                        # Check intermediate sizes, not just the final drag position.
                        for extra in (200, 300, 400, 250):
                            app.geometry(f'{natural + app.px(430 + extra)}x{app.px(800)}')
                            app.update()
                            canvas = app.stats.canvas
                            width = canvas.winfo_width()
                            self.assertGreater(width, natural)
                            self.assertEqual(app.stats.content.winfo_width(), width)
                            saved = app.original_labels[0]
                            saved_x = saved.winfo_x()
                            right_gap = width - saved_x - saved.winfo_width()
                            self.assertLessEqual(right_gap, app.px(8))
                            if previous_width is not None:
                                self.assertEqual(saved_x - previous_saved_x, width - previous_width)
                            previous_width, previous_saved_x = width, saved_x
                            self.assertTrue(canvas.winfo_ismapped())
                            self.assertEqual(app.notebook.bar.grid_info()['row'], 0)
                            self.assertGreater(app.notebook.bar.winfo_rootx(),
                                               app.toolbar.winfo_rootx() + app.toolbar.winfo_width())
                            self.assertLessEqual(abs(app.notebook.bar.winfo_rooty() - app.toolbar.winfo_rooty()), app.px(5))
                        self.assertTrue(app.launch_button.winfo_ismapped())
                        app.notebook.select(app.limits_page)
                        app.update()
                        self.assertTrue(app.limits_page.winfo_ismapped())
                        self.assertTrue(app.toolbar.winfo_ismapped())
                        self.assertFalse(hasattr(app.limits_page, 'toolbar'))
                        self.assertEqual(app.notebook.bar.grid_info()['row'], 0)
                    finally:
                        app.destroy()
