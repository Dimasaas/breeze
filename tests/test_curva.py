import json
import tempfile
import unittest
from pathlib import Path

from breeze.curva import ConfigInvalida, Configuracao, carregar


class TestCurva(unittest.TestCase):
    def setUp(self):
        self.cfg = Configuracao()

    def test_abaixo_do_primeiro_ponto_fica_no_primeiro(self):
        self.assertEqual(self.cfg.rpm_para(20), 2000)

    def test_acima_do_ultimo_ponto_fica_no_ultimo(self):
        self.assertEqual(self.cfg.rpm_para(95), 6200)

    def test_interpola_linearmente(self):
        self.assertAlmostEqual(self.cfg.rpm_para(54), 2300)  # meio de 50->58

    def test_passa_exatamente_pelos_pontos(self):
        for t, r in self.cfg.curva:
            self.assertAlmostEqual(self.cfg.rpm_para(t), r)

    def test_curva_e_monotona(self):
        anterior = 0
        for t in range(20, 100):
            r = self.cfg.rpm_para(t)
            self.assertGreaterEqual(r, anterior)
            anterior = r

    def test_rejeita_temperaturas_nao_crescentes(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao(curva=((50, 2000), (50, 3000)))

    def test_rejeita_rpm_que_cai(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao(curva=((50, 3000), (60, 2000)))

    def test_rejeita_curva_curta(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao(curva=((50, 2000),))

    def test_rejeita_emergencia_acima_de_88(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao(emergencia_c=95)

    def test_rejeita_curva_que_passa_da_emergencia(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao(curva=((50, 2000), (90, 6000)), emergencia_c=88)

    def test_de_dict_usa_padroes_para_campos_ausentes(self):
        cfg = Configuracao.de_dict({"piso_rpm": 2200})
        self.assertEqual(cfg.piso_rpm, 2200)
        self.assertEqual(cfg.emergencia_c, 88.0)

    def test_de_dict_rejeita_lixo(self):
        with self.assertRaises(ConfigInvalida):
            Configuracao.de_dict({"curva": "x"})
        with self.assertRaises(ConfigInvalida):
            Configuracao.de_dict([1, 2])

    def test_carrega_json_do_disco(self):
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / "c.json"
            arq.write_text(json.dumps(self.cfg.como_dict()), encoding="utf-8")
            self.assertEqual(carregar(arq), self.cfg)

    def test_json_quebrado_e_arquivo_ausente(self):
        with tempfile.TemporaryDirectory() as d:
            ruim = Path(d) / "ruim.json"
            ruim.write_text("{", encoding="utf-8")
            with self.assertRaises(ConfigInvalida):
                carregar(ruim)
            with self.assertRaises(ConfigInvalida):
                carregar(Path(d) / "nao-existe.json")


if __name__ == "__main__":
    unittest.main()
