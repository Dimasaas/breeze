import unittest

from breeze.controle import Controlador
from breeze.curva import Configuracao


def novo(**kw):
    return Controlador(Configuracao(**kw), rpm_max=6200)


class TestCurvaNoControlador(unittest.TestCase):
    def test_frio_fica_no_piso(self):
        self.assertEqual(novo().decidir(30).rpm, 2000)

    def test_piso_de_2000_vale_mesmo_com_curva_mais_baixa(self):
        c = Controlador(Configuracao(curva=((40, 800), (80, 6000)), piso_rpm=2000))
        self.assertEqual(c.decidir(41).rpm, 2000)

    def test_acompanha_a_curva_subindo(self):
        self.assertEqual(novo().decidir(66).rpm, 3400)

    def test_nunca_passa_do_maximo_do_hardware(self):
        c = Controlador(Configuracao(), rpm_max=5000)
        self.assertEqual(c.decidir(87).rpm, 5000)


class TestHisterese(unittest.TestCase):
    def test_oscilacao_dentro_da_banda_nao_mexe_no_rpm(self):
        c = novo(histerese_c=3.0)
        c.decidir(70)
        pedidos = {c.decidir(t).rpm for t in (69, 70, 69.5, 68.5, 69.9, 68)}
        self.assertEqual(len(pedidos), 1)

    def test_motivo_histerese_quando_segura(self):
        c = novo()
        c.decidir(70)
        self.assertEqual(c.decidir(68.5).motivo, "histerese")

    def test_sobe_na_hora(self):
        c = novo()
        antes = c.decidir(60).rpm
        self.assertGreater(c.decidir(70).rpm, antes)

    def test_desce_so_depois_de_cair_alem_da_banda(self):
        c = novo(histerese_c=3.0)
        alto = c.decidir(74).rpm
        self.assertEqual(c.decidir(71.5).rpm, alto)      # ainda dentro da banda
        self.assertLess(c.decidir(70.0).rpm, alto)       # caiu mais que 3 C

    def test_histerese_zero_acompanha_sempre(self):
        c = novo(histerese_c=0)
        a = c.decidir(70).rpm
        self.assertLess(c.decidir(69).rpm, a)


class TestEmergencia(unittest.TestCase):
    def test_88_graus_vai_ao_maximo(self):
        d = novo().decidir(88.0)
        self.assertEqual((d.rpm, d.motivo), (6200, "emergencia"))

    def test_87_nao_e_emergencia(self):
        self.assertNotEqual(novo().decidir(87.0).motivo, "emergencia")

    def test_trava_so_solta_com_folga(self):
        c = novo()
        c.decidir(89)
        self.assertEqual(c.decidir(86).motivo, "emergencia")   # ainda travado
        self.assertEqual(c.decidir(85).motivo, "emergencia")
        self.assertNotEqual(c.decidir(83).motivo, "emergencia")
        self.assertFalse(c.em_emergencia)

    def test_emergencia_configuravel_mais_baixa(self):
        c = novo(emergencia_c=80, curva=((50, 2000), (80, 6200)))
        self.assertEqual(c.decidir(80).rpm, 6200)


class TestFalhaDeSensor(unittest.TestCase):
    def test_sem_leitura_vai_ao_maximo(self):
        d = novo().decidir(None)
        self.assertEqual((d.rpm, d.motivo), (6200, "sensor"))

    def test_nan_conta_como_falha(self):
        self.assertEqual(novo().decidir(float("nan")).motivo, "sensor")

    def test_recupera_quando_o_sensor_volta(self):
        c = novo()
        c.decidir(None)
        d = c.decidir(45)
        self.assertEqual((d.rpm, d.motivo), (2000, "curva"))


if __name__ == "__main__":
    unittest.main()
