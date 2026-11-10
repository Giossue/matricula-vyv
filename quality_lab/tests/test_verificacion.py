"""Casos V01–V09 del Laboratorio de Verificación.

Cada prueba informa los datos que usó y el resultado que obtuvo
(self.registrar). El laboratorio muestra exactamente eso.
"""

from django.contrib.auth import SESSION_KEY
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from campusflow import fabricas as f
from enrollments import services
from enrollments.models import DetalleMatricula, Matricula
from quality_lab.soporte import CasoVyVMixin, caso


class CasosVerificacion(CasoVyVMixin, TestCase):
    def setUp(self):
        self.periodo = f.periodo()
        self.ana = f.estudiante("ana.prueba")

    def intentar(self, estudiante, ids):
        """Intenta matricular y devuelve las incidencias ([] si se aceptó)."""
        try:
            services.confirmar_matricula(estudiante, ids)
        except services.MatriculaRechazada as error:
            return error.incidencias
        return []

    @staticmethod
    def describir(incidencias):
        if not incidencias:
            return "La matrícula fue ACEPTADA (la regla no se aplicó)"
        reglas = [i.regla for i in incidencias]
        return f"Rechazada con {reglas}: «{incidencias[0].mensaje}»"

    @caso("V01")
    def test_v01_inicio_sesion_correcto(self):
        """V01 · Un usuario con credenciales válidas inicia sesión."""
        self.registrar(datos="Usuario «ana.prueba» (estudiante) con su contraseña correcta.")
        r = self.client.post(reverse("accounts:login"), {"username": "ana.prueba", "password": f.CLAVE}, follow=True)
        autenticado = SESSION_KEY in self.client.session
        destino = r.redirect_chain[-1][0] if r.redirect_chain else r.request["PATH_INFO"]
        self.registrar(obtenido=f"Sesión autenticada: {'sí' if autenticado else 'no'}; destino final {destino}; HTTP {r.status_code}.")
        self.assertTrue(autenticado)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(destino, reverse("enrollments:panel"))

    @caso("V02")
    def test_v02_rechazo_credenciales_incorrectas(self):
        """V02 · Una contraseña incorrecta no permite iniciar sesión."""
        self.registrar(datos="Usuario «ana.prueba» con la contraseña «incorrecta123».")
        r = self.client.post(reverse("accounts:login"), {"username": "ana.prueba", "password": "incorrecta123"})
        autenticado = SESSION_KEY in self.client.session
        mensaje = "Usuario o contraseña incorrectos" in r.content.decode()
        self.registrar(obtenido=f"HTTP {r.status_code} en el formulario; sesión creada: {'sí' if autenticado else 'no'}; "
                                f"mensaje de error visible: {'sí' if mensaje else 'no'}.")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(autenticado)
        self.assertTrue(mensaje)

    @caso("V03")
    def test_v03_registro_exitoso_matricula(self):
        """V03 · Una selección válida crea la matrícula y su detalle."""
        seccion = f.seccion(f.asignatura("Programación I"), self.periodo, capacidad=10)
        self.registrar(datos=f"Estudiante sin matrícula; sección «{seccion}» con 10 cupos libres.")
        resultado = services.confirmar_matricula(self.ana, [seccion.pk])
        detalles = list(resultado.matricula.detalles.values_list("estado", flat=True))
        self.registrar(obtenido=f"Matrícula {resultado.matricula.codigo} creada con {len(detalles)} detalle(s) "
                                f"en estado {detalles}; cupos disponibles ahora: {seccion.cupos_disponibles}/10.")
        self.assertEqual(Matricula.objects.filter(estudiante=self.ana).count(), 1)
        self.assertEqual(detalles, ["inscrita"])
        self.assertEqual(seccion.cupos_disponibles, 9)

    @caso("V04")
    def test_v04_bloqueo_asignatura_duplicada(self):
        """V04 · No se matricula dos veces la misma asignatura en el período."""
        asig = f.asignatura("Matemática Discreta")
        a = f.seccion(asig, self.periodo, "A", bloques=((2, "07:00", "09:00"),))
        b = f.seccion(asig, self.periodo, "B", bloques=((5, "15:00", "17:00"),))
        services.confirmar_matricula(self.ana, [a.pk])
        self.registrar(datos="Ana ya tiene Matemática Discreta paralelo A e intenta el paralelo B.")
        antes = DetalleMatricula.objects.count()
        incidencias = self.intentar(self.ana, [b.pk])
        reglas = [i.regla for i in incidencias]
        self.registrar(obtenido=f"{self.describir(incidencias)}. Detalles en BD: {antes} → {DetalleMatricula.objects.count()}.")
        self.assertEqual(reglas, [services.ASIGNATURA_DUPLICADA])
        self.assertEqual(DetalleMatricula.objects.count(), antes)

    @caso("V05")
    def test_v05_bloqueo_sin_cupos(self):
        """V05 · No se supera la capacidad máxima de una sección."""
        seccion = f.seccion(f.asignatura("Base de Datos I"), self.periodo, capacidad=1)
        bruno = f.estudiante("bruno.prueba")
        services.confirmar_matricula(bruno, [seccion.pk])
        self.registrar(datos=f"Sección «{seccion}» con capacidad 1 ocupada por Bruno; Ana intenta matricularse.")
        incidencias = self.intentar(self.ana, [seccion.pk])
        reglas = [i.regla for i in incidencias]
        inscritos = seccion.detalles.filter(estado="inscrita").count()
        sin_matricula = "sí" if not Matricula.objects.filter(estudiante=self.ana).exists() else "no"
        self.registrar(obtenido=f"{self.describir(incidencias)}. Inscritos {inscritos}/1; Ana sin matrícula: {sin_matricula}.")
        self.assertEqual(reglas, [services.CUPO_AGOTADO])
        self.assertEqual(inscritos, 1)

    @caso("V06")
    def test_v06_deteccion_cruce_horarios(self):
        """V06 · Dos secciones con horario superpuesto no se matriculan juntas."""
        p1 = f.seccion(f.asignatura("Programación I"), self.periodo, bloques=((1, "07:00", "09:00"),))
        poo = f.seccion(f.asignatura("Programación OO"), self.periodo, bloques=((1, "08:00", "10:00"),))
        self.registrar(datos="Programación I (lunes 07:00–09:00) + Programación OO (lunes 08:00–10:00) en la misma confirmación.")
        incidencias = self.intentar(self.ana, [p1.pk, poo.pk])
        reglas = [i.regla for i in incidencias]
        guardados = DetalleMatricula.objects.filter(matricula__estudiante=self.ana).count()
        self.registrar(obtenido=f"{self.describir(incidencias)}. Detalles guardados para Ana: {guardados}.")
        self.assertEqual(reglas, [services.CRUCE_HORARIO])
        self.assertEqual(guardados, 0)

    @caso("V07")
    def test_v07_persistencia_datos(self):
        """V07 · La matrícula hecha desde la web queda escrita en las tablas SQLite."""
        seccion = f.seccion(f.asignatura("Estadística"), self.periodo)
        self.client.force_login(self.ana.usuario)
        self.registrar(datos=f"POST a /estudiante/matricula/confirmar/ con la sección {seccion.pk} como «ana.prueba».")
        r = self.client.post(reverse("enrollments:confirmar"), {"secciones": [seccion.pk]})
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT d.estado, m.estudiante_id FROM detalles_matricula d "
                "JOIN matriculas m ON m.id = d.matricula_id WHERE d.seccion_id = %s",
                [seccion.pk],
            )
            filas = cursor.fetchall()
        self.registrar(obtenido=f"HTTP {r.status_code} (redirección al comprobante); SQL directo sobre "
                                f"detalles_matricula devolvió {filas}.")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(filas, [("inscrita", self.ana.pk)])

    @caso("V08")
    def test_v08_restriccion_acceso_por_rol(self):
        """V08 · Un estudiante no accede a administración ni a matrículas ajenas."""
        otra = f.estudiante("carla.prueba")
        seccion = f.seccion(f.asignatura("Álgebra"), self.periodo)
        ajena = services.confirmar_matricula(otra, [seccion.pk]).matricula
        self.client.force_login(self.ana.usuario)
        self.registrar(datos=f"Sesión de «ana.prueba» solicita /administracion/ y el comprobante de la matrícula {ajena.pk} de Carla.")
        r_admin = self.client.get(reverse("academics:panel"))
        r_lab = self.client.get(reverse("quality_lab:verificacion"))
        r_ajena = self.client.get(reverse("enrollments:comprobante", args=[ajena.pk]))
        r_retiro = self.client.post(reverse("enrollments:retirar", args=[ajena.detalles.first().pk]))
        sigue = ajena.detalles.first().estado
        self.registrar(obtenido=f"Panel admin HTTP {r_admin.status_code}; laboratorio HTTP {r_lab.status_code}; "
                                f"matrícula ajena HTTP {r_ajena.status_code}; intento de retirar asignatura ajena: "
                                f"estado sigue «{sigue}».")
        self.assertEqual(r_admin.status_code, 403)
        self.assertEqual(r_lab.status_code, 403)
        self.assertEqual(r_ajena.status_code, 404)
        self.assertEqual(sigue, "inscrita")

    @caso("V09")
    def test_v09_recuperacion_cupo_tras_cancelacion(self):
        """V09 · Retirar una asignatura dentro del plazo libera su cupo."""
        seccion = f.seccion(f.asignatura("Ingeniería de Requisitos"), self.periodo, capacidad=1)
        bruno = f.estudiante("bruno.prueba")
        detalle = services.confirmar_matricula(self.ana, [seccion.pk]).detalles_creados[0]
        self.registrar(datos="Sección con capacidad 1 ocupada por Ana; Ana la retira y luego Bruno intenta matricularse.")
        antes = seccion.cupos_disponibles
        services.retirar_asignatura(self.ana, detalle.pk)
        despues = seccion.cupos_disponibles
        services.confirmar_matricula(bruno, [seccion.pk])
        final = seccion.cupos_disponibles
        detalle.refresh_from_db()
        self.registrar(obtenido=f"Cupos disponibles: {antes} → {despues} tras el retiro; Bruno matriculado; "
                                f"cupos ahora {final}. Detalle de Ana en estado «{detalle.estado}» (se conserva el historial).")
        self.assertEqual((antes, despues, final), (0, 1, 0))
        self.assertEqual(detalle.estado, "retirada")
