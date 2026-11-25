import tempfile
import unittest
from pathlib import Path

from ventoinha_macbook.simulador import arvore_falsa, definir_temperatura
from ventoinha_macbook.sysfs import Applesmc, ErroSysfs


class TestApplesmc(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.dir = arvore_falsa(self.raiz, temp_c=52.0)
        self.smc = Applesmc(self.raiz)

    def test_le_a_maior_temperatura_de_cpu_e_ignora_outros_sensores(self):
        definir_temperatura(self.raiz, 61.5, sensor=2)
        self.assertEqual(self.smc.temperatura(), 61.5)  # o TB0T de 99 C nao conta

    def test_sensor_com_valor_absurdo_e_descartado(self):
        for i in (1, 2, 3):
            definir_temperatura(self.raiz, 200, sensor=i)
        self.assertIsNone(self.smc.temperatura())

    def test_sensor_ilegivel_e_pulado(self):
        (self.dir / "temp1_input").write_text("lixo\n")
        self.assertEqual(self.smc.temperatura(), 52.0)

    def test_sem_nenhum_sensor_devolve_none(self):
        for arq in self.dir.glob("temp*_input"):
            arq.unlink()
        self.assertIsNone(self.smc.temperatura())

    def test_sem_rotulo_usa_todos_os_sensores(self):
        for arq in self.dir.glob("temp*_label"):
            arq.unlink()
        self.assertEqual(self.smc.temperatura(), 99.0)

    def test_escreve_manual_e_rpm(self):
        self.smc.definir_manual(True)
        self.smc.pedir_rpm(3300)
        self.assertEqual((self.dir / "fan1_manual").read_text(), "1")
        self.assertEqual((self.dir / "fan1_output").read_text(), "3300")
        self.assertTrue(self.smc.modo_manual())

    def test_rpm_max_e_min_reportado(self):
        self.assertEqual(self.smc.rpm_max(), 6200)
        self.assertEqual(self.smc.rpm_min_reportado(), 4000)

    def test_rpm_max_ausente_usa_padrao(self):
        (self.dir / "fan1_max").unlink()
        self.assertEqual(self.smc.rpm_max(), 6200)

    def test_somente_leitura_nao_escreve(self):
        smc = Applesmc(self.raiz, somente_leitura=True)
        with self.assertRaises(ErroSysfs):
            smc.pedir_rpm(3000)
        self.assertEqual((self.dir / "fan1_output").read_text().strip(), "0")

    def test_falha_de_escrita_vira_erro_sysfs(self):
        (self.dir / "fan1_output").unlink()
        (self.dir / "fan1_output").mkdir()  # escrever num diretorio falha
        with self.assertRaises(ErroSysfs):
            self.smc.pedir_rpm(3000)


if __name__ == "__main__":
    unittest.main()
