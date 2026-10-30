import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from organizador import organize, plan, LOG_NAME


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_dry_run_changes_nothing(self):
        (self.root/'teste.PDF').write_bytes(b'fictional')
        result = organize(self.root)
        self.assertEqual(result[0]['status'], 'simulado')
        self.assertEqual([p.name for p in self.root.iterdir()], ['teste.PDF'])

    def test_categories_and_content_preserved(self):
        cases = {'a.pdf':'Documentos','b.PNG':'Imagens','c.mp4':'Videos','d.mp3':'Musicas','e.xlsx':'Planilhas','f.zip':'Compactados','g.abc':'Outros'}
        for name in cases: (self.root/name).write_bytes(name.encode())
        records = organize(self.root, apply=True)
        self.assertEqual(len(records),7)
        self.assertTrue(all(r['status']=='movido' for r in records))
        for name, category in cases.items():
            self.assertEqual((self.root/category/name).read_bytes(),name.encode())
        self.assertEqual(len((self.root/LOG_NAME).read_text().splitlines()),7)

    def test_collision_does_not_overwrite(self):
        (self.root/'Documentos').mkdir()
        (self.root/'Documentos/a.pdf').write_bytes(b'keep')
        (self.root/'a.pdf').write_bytes(b'new')
        organize(self.root, apply=True)
        self.assertEqual((self.root/'Documentos/a.pdf').read_bytes(),b'keep')
        self.assertEqual((self.root/'Documentos/a (1).pdf').read_bytes(),b'new')

    def test_ignores_subfolders_hidden_and_incomplete(self):
        (self.root/'sub').mkdir(); (self.root/'sub/a.pdf').write_bytes(b'keep')
        for name in ['.hidden','a.crdownload',LOG_NAME]: (self.root/name).write_bytes(b'keep')
        self.assertEqual(plan(self.root),[])

    def test_repeated_run_is_safe(self):
        (self.root/'a.txt').write_text('fictional')
        organize(self.root,apply=True)
        self.assertEqual(organize(self.root,apply=True),[])

    def test_symlink_is_not_followed(self):
        (self.root/'a.pdf').symlink_to(self.root/'missing')
        self.assertEqual(plan(self.root),[])

    def test_invalid_category_aborts_before_moving(self):
        (self.root/'Documentos').write_text('existing file')
        (self.root/'a.pdf').write_text('keep')
        with self.assertRaises(ValueError): organize(self.root,apply=True)
        self.assertTrue((self.root/'a.pdf').exists())

    def test_copy_fallback(self):
        (self.root/'a.pdf').write_bytes(b'fictional')
        with patch('organizador.os.link',side_effect=OSError('unsupported')):
            result=organize(self.root,apply=True)
        self.assertEqual(result[0]['status'],'movido')
        self.assertEqual((self.root/'Documentos/a.pdf').read_bytes(),b'fictional')

    def test_move_failure_preserves_origin_and_logs(self):
        (self.root/'a.pdf').write_bytes(b'keep')
        with patch('organizador.os.link',side_effect=FileExistsError('race')):
            records=organize(self.root,apply=True)
        self.assertEqual(records[0]['status'],'erro')
        self.assertEqual((self.root/'a.pdf').read_bytes(),b'keep')
        self.assertEqual(json.loads((self.root/LOG_NAME).read_text())['status'],'erro')

    def test_failed_copy_preserves_source_and_removes_partial_output(self):
        (self.root/'a.pdf').write_bytes(b'keep')
        with patch('organizador.os.link',side_effect=OSError('unsupported')):
            with patch('organizador.shutil.copyfileobj',side_effect=OSError('disk full')):
                records=organize(self.root,apply=True)
        self.assertEqual(records[0]['status'],'erro')
        self.assertEqual((self.root/'a.pdf').read_bytes(),b'keep')
        self.assertFalse((self.root/'Documentos/a.pdf').exists())


if __name__=='__main__':unittest.main()
