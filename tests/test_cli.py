import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from breeze import cli
from breeze.simulador import arvore_falsa, definir_temperatura


def rodar(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        codigo = cli.main(list(args))
    return codigo, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

    def test_padrao_imprime_json_valido(self):
        codigo, out, _ = rodar("--padrao")
        self.assertEqual(codigo, 0)
        dados = json.loads(out)
        self.assertEqual(dados["piso_rpm"], 2000)
        self.assertEqual(dados["emergencia_c"], 88.0)

    def test_validar_aceita_o_exemplo_do_repositorio(self):
        exemplo = Path(__file__).resolve().parent.parent / "systemd" / "breeze.json"
        codigo, out, _ = rodar("--validar", str(exemplo))
        self.assertEqual(codigo, 0, out)

    def test_validar_rejeita_config_ruim(self):
        ruim = self.raiz / "ruim.json"
        ruim.write_text(json.dumps({"curva": [[60, 3000], [50, 2000]]}))
        codigo, out, _ = rodar("--validar", str(ruim))
        self.assertEqual(codigo, 1)
        self.assertIn("invalido", out)

    def test_simular_imprime_a_decisao_e_nao_escreve(self):
        arv = arvore_falsa(self.raiz, temp_c=66)
        codigo, out, _ = rodar("--simular", "--raiz", str(self.raiz), "--ciclos", "1",
                               "--config", str(self.raiz / "nao-existe.json"))
        self.assertEqual(codigo, 0)
        self.assertIn("3400 rpm", out)
        self.assertEqual((arv / "fan1_output").read_text().strip(), "0")
        self.assertEqual((arv / "fan1_manual").read_text().strip(), "0")

    def test_simular_com_sensor_em_emergencia(self):
        arvore_falsa(self.raiz)
        definir_temperatura(self.raiz, 90)
        _, out, _ = rodar("--simular", "--raiz", str(self.raiz), "--ciclos", "1")
        self.assertIn("emergencia", out)

    def test_sem_applesmc_sai_com_codigo_3(self):
        codigo, _, err = rodar("--raiz", str(self.raiz), "--ciclos", "1")
        self.assertEqual(codigo, 3)
        self.assertIn("applesmc", err)


if __name__ == "__main__":
    unittest.main()
