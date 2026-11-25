import signal
import tempfile
import unittest
from pathlib import Path

from breeze.curva import Configuracao
from breeze.daemon import Daemon, ErroFatal
from breeze.simulador import MaquinaTermica, arvore_falsa, definir_temperatura
from breeze.sysfs import Applesmc

CFG_1S = Configuracao(intervalo_s=1.0)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.dir = arvore_falsa(self.raiz, temp_c=45.0)
        self.linhas = []
        self.smc = Applesmc(self.raiz)

    def daemon(self, cfg=None, **kw):
        return Daemon(self.smc, cfg or Configuracao(), saida=self.linhas.append, **kw)

    def lido(self, nome):
        return (self.dir / nome).read_text().strip()

    def quebrar_escrita(self):
        (self.dir / "fan1_output").unlink()
        (self.dir / "fan1_output").mkdir()   # escrever num diretorio falha


class TestCiclo(Base):
    def test_escreve_o_rpm_decidido(self):
        d = self.daemon()
        definir_temperatura(self.raiz, 66)
        d.ciclo()
        self.assertEqual(self.lido("fan1_output"), "3400")

    def test_sensor_morto_pede_o_maximo(self):
        d = self.daemon()
        for arq in self.dir.glob("temp*_input"):
            arq.unlink()
        d.ciclo()
        self.assertEqual(self.lido("fan1_output"), "6200")
        self.assertTrue(any("ATENCAO" in x for x in self.linhas))

    def test_sensor_com_lixo_pede_o_maximo(self):
        d = self.daemon()
        for arq in self.dir.glob("temp*_input"):
            arq.write_text("???\n")
        d.ciclo()
        self.assertEqual(self.lido("fan1_output"), "6200")

    def test_emergencia_pede_o_maximo(self):
        d = self.daemon()
        definir_temperatura(self.raiz, 88)
        d.ciclo()
        self.assertEqual(self.lido("fan1_output"), "6200")

    def test_retoma_o_manual_se_outro_programa_desligar(self):
        d = self.daemon()
        self.smc.definir_manual(True)
        d.ciclo()
        (self.dir / "fan1_manual").write_text("0\n")
        d.ciclo()
        self.assertEqual(self.lido("fan1_manual"), "1")

    def test_erros_de_escrita_seguidos_viram_erro_fatal(self):
        d = self.daemon()
        self.quebrar_escrita()
        with self.assertRaises(ErroFatal):
            for _ in range(10):
                d.ciclo()


class TestCicloDeVida(Base):
    def test_liga_o_manual_e_devolve_ao_automatico_no_fim(self):
        d = self.daemon()
        estados = []
        d.executar(ciclos=3, dormir=lambda s: estados.append(self.lido("fan1_manual")))
        self.assertEqual(estados, ["1", "1", "1"])
        self.assertEqual(self.lido("fan1_manual"), "0")

    def test_sigterm_para_o_laco_e_devolve_o_controle(self):
        d = self.daemon()
        n = []

        def dormir(_s):
            n.append(1)
            if len(n) == 2:
                # o que o systemd faz: manda SIGTERM; chamamos o handler instalado
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        anterior = signal.getsignal(signal.SIGTERM)
        self.addCleanup(signal.signal, signal.SIGTERM, anterior)
        self.addCleanup(signal.signal, signal.SIGINT, signal.getsignal(signal.SIGINT))
        d.executar(dormir=dormir)
        self.assertEqual(len(n), 2)
        self.assertEqual(self.lido("fan1_manual"), "0")

    def test_devolve_o_controle_mesmo_com_erro_fatal(self):
        d = self.daemon()
        self.quebrar_escrita()
        with self.assertRaises(ErroFatal):
            d.executar(dormir=lambda s: None)
        self.assertEqual(self.lido("fan1_manual"), "0")

    def test_simular_nao_escreve_nada(self):
        smc = Applesmc(self.raiz, somente_leitura=True)
        d = Daemon(smc, Configuracao(), simular=True, saida=self.linhas.append)
        definir_temperatura(self.raiz, 70)
        d.executar(ciclos=2, dormir=lambda s: None)
        self.assertEqual(self.lido("fan1_output"), "0")
        self.assertEqual(self.lido("fan1_manual"), "0")
        self.assertEqual(len(self.linhas), 2)
        self.assertIn("rpm", self.linhas[0])


class TestSimuladorTermico(Base):
    def test_carga_alta_aquece_mas_a_ventoinha_segura_abaixo_da_emergencia(self):
        m = MaquinaTermica(self.raiz, carga=0.9)
        self.daemon(CFG_1S).executar(ciclos=500, dormir=lambda s: m.passo(1.0))
        self.assertLess(m.pico, 88.0)
        self.assertGreater(m.pico, 55.0)

    def test_resfria_e_volta_ao_piso_quando_a_carga_cessa(self):
        m = MaquinaTermica(self.raiz, carga=0.9)
        self.daemon(CFG_1S).executar(ciclos=400, dormir=lambda s: m.passo(1.0))
        self.assertGreater(m.rpm, 3000)
        m.carga = 0.02
        self.daemon(CFG_1S).executar(ciclos=700, dormir=lambda s: m.passo(1.0))
        self.assertLessEqual(m.rpm, 2100)

    def test_carga_oscilante_nao_faz_a_ventoinha_cacar_rotacao(self):
        m = MaquinaTermica(self.raiz, carga=0.5)
        pedidos = []

        def dormir(_s):
            m.carga = 0.5 + (0.08 if (len(pedidos) // 5) % 2 else -0.08)
            m.passo(1.0)
            pedidos.append(int(self.lido("fan1_output")))

        self.daemon(CFG_1S).executar(ciclos=400, dormir=dormir)
        ultimos = pedidos[-200:]
        trocas = sum(1 for a, b in zip(ultimos, ultimos[1:]) if a != b)
        self.assertLess(trocas, 30)

    def test_sensor_que_morre_no_meio_leva_ao_maximo(self):
        m = MaquinaTermica(self.raiz, carga=0.3)
        n = []

        def dormir(_s):
            n.append(1)
            if len(n) == 100:
                for arq in self.dir.glob("temp*_input"):
                    arq.unlink()
            elif len(n) < 100:
                m.passo(1.0)

        self.daemon(CFG_1S).executar(ciclos=105, dormir=dormir)
        self.assertEqual(self.lido("fan1_output"), "6200")


if __name__ == "__main__":
    unittest.main()
