"""Pruebas del horario de atención (RN-21, RN-22, RN-23).

Se ejercita `apps.citas.agenda`, que decide si una cita cabe en el horario del
negocio. Es lógica pura sobre fechas, así que las pruebas heredan de
`SimpleTestCase` y no tocan la base de datos.

Las fechas se construyen en la zona local de la barbería: la comparación con el
horario de atención ocurre en ese huso, no en UTC (RN-17).
"""

from datetime import datetime, timedelta

from django.test import SimpleTestCase

from apps.citas.agenda import (
    HORA_APERTURA,
    HORA_CIERRE,
    INTERVALO_MIN,
    ZONA_LOCAL,
    HorarioInvalido,
    es_dia_laborable,
    horarios_del_dia,
    verificar_horario,
)

# Semana de referencia: lunes 5 de enero de 2026 a domingo 11.
LUNES = datetime(2026, 1, 5).date()
DOMINGO = datetime(2026, 1, 11).date()


def momento(dia, hora, minuto=0):
    """Instante en la zona horaria de la barbería."""
    return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=ZONA_LOCAL)


class DiasDeAtencion(SimpleTestCase):
    """RN-21: la barbería no atiende todos los días."""

    def test_lunes_es_laborable(self):
        self.assertTrue(es_dia_laborable(LUNES))

    def test_domingo_no_es_laborable(self):
        self.assertFalse(es_dia_laborable(DOMINGO))

    def test_rechaza_cita_en_domingo(self):
        with self.assertRaises(HorarioInvalido) as fallo:
            verificar_horario(momento(DOMINGO, HORA_APERTURA + 1), 30)
        self.assertIn("no atiende", str(fallo.exception))

    def test_domingo_no_genera_horarios(self):
        self.assertEqual(horarios_del_dia(DOMINGO, 30), [])


class FranjaDeAtencion(SimpleTestCase):
    """RN-21 y RN-23: la cita empieza y termina dentro del horario."""

    def test_acepta_horario_dentro_de_la_franja(self):
        verificar_horario(momento(LUNES, HORA_APERTURA + 1), 30)

    def test_rechaza_antes_de_la_apertura(self):
        with self.assertRaises(HorarioInvalido) as fallo:
            verificar_horario(momento(LUNES, HORA_APERTURA - 1), 30)
        self.assertIn("abre", str(fallo.exception))

    def test_rechaza_a_partir_del_cierre(self):
        with self.assertRaises(HorarioInvalido) as fallo:
            verificar_horario(momento(LUNES, HORA_CIERRE), 30)
        self.assertIn("cierra", str(fallo.exception))

    def test_rechaza_servicio_que_no_termina_antes_del_cierre(self):
        """El inicio es válido, pero la duración se pasa de la hora de cierre."""
        inicio = momento(LUNES, HORA_CIERRE - 1)
        with self.assertRaises(HorarioInvalido) as fallo:
            verificar_horario(inicio, 120)
        self.assertIn("no alcanza a terminar", str(fallo.exception))

    def test_acepta_servicio_que_termina_justo_en_el_cierre(self):
        inicio = momento(LUNES, HORA_CIERRE - 1)
        verificar_horario(inicio, 60)


class IntervalosDeInicio(SimpleTestCase):
    """RN-22: los inicios ocurren en intervalos regulares."""

    def test_acepta_inicio_en_punto(self):
        verificar_horario(momento(LUNES, HORA_APERTURA + 1, 0), 30)

    def test_acepta_inicio_en_el_intervalo(self):
        verificar_horario(momento(LUNES, HORA_APERTURA + 1, INTERVALO_MIN), 30)

    def test_rechaza_minuto_fuera_del_intervalo(self):
        desalineado = (INTERVALO_MIN + 1) % 60
        with self.assertRaises(HorarioInvalido) as fallo:
            verificar_horario(momento(LUNES, HORA_APERTURA + 1, desalineado), 30)
        self.assertIn(f"cada {INTERVALO_MIN} minutos", str(fallo.exception))

    def test_rechaza_segundos_en_el_inicio(self):
        con_segundos = momento(LUNES, HORA_APERTURA + 1).replace(second=30)
        with self.assertRaises(HorarioInvalido):
            verificar_horario(con_segundos, 30)


class HorariosGenerados(SimpleTestCase):
    """Los horarios ofrecidos deben ser reservables uno por uno."""

    def test_todos_los_horarios_pasan_la_verificacion(self):
        """Coherencia entre lo que se ofrece y lo que se acepta.

        Si un horario generado fuera rechazado al reservar, quien agenda vería
        un error tras elegir una opción que la propia interfaz le ofreció.
        """
        for inicio in horarios_del_dia(LUNES, 30):
            verificar_horario(inicio, 30)

    def test_empieza_en_la_apertura(self):
        primero = horarios_del_dia(LUNES, 30)[0]
        self.assertEqual(primero.astimezone(ZONA_LOCAL).hour, HORA_APERTURA)

    def test_separados_por_el_intervalo(self):
        horarios = horarios_del_dia(LUNES, 30)
        for previo, siguiente in zip(horarios, horarios[1:]):
            self.assertEqual(siguiente - previo, timedelta(minutes=INTERVALO_MIN))

    def test_el_ultimo_termina_antes_del_cierre(self):
        """RN-23 aplicado a la generación, no solo a la verificación."""
        duracion = 60
        ultimo = horarios_del_dia(LUNES, duracion)[-1]
        fin = (ultimo + timedelta(minutes=duracion)).astimezone(ZONA_LOCAL)
        self.assertLessEqual(fin.hour, HORA_CIERRE)

    def test_un_servicio_largo_ofrece_menos_horarios(self):
        self.assertLess(
            len(horarios_del_dia(LUNES, 120)),
            len(horarios_del_dia(LUNES, 30)),
        )


class ConversionDeHuso(SimpleTestCase):
    """RN-17: la base guarda en UTC; el horario se juzga en hora local."""

    def test_un_instante_utc_se_juzga_en_hora_local(self):
        """El mismo instante, expresado en UTC, debe aceptarse igual.

        Comparar sin convertir rechazaría una cita perfectamente válida.
        """
        local = momento(LUNES, HORA_APERTURA + 1)
        verificar_horario(local.astimezone(tz=None), 30)
