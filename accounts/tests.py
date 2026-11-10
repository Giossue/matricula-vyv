from django.contrib.auth import SESSION_KEY
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from campusflow import fabricas as f

from .models import Usuario


class UsuarioModeloTests(TestCase):
    def test_contrasena_se_guarda_como_hash(self):
        """La contraseña se almacena con hash y no en texto plano."""
        u = f.estudiante("ana.hash").usuario
        self.assertNotEqual(u.password, f.CLAVE)
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(u.check_password(f.CLAVE))

    def test_roles_y_nombre_completo(self):
        """El rol determina si el usuario es administrador o estudiante."""
        admin = f.administrador()
        est = f.estudiante("bruno.rol").usuario
        self.assertTrue(admin.es_administrador)
        self.assertFalse(admin.es_estudiante)
        self.assertTrue(est.es_estudiante)
        self.assertEqual(est.nombre_completo, "Bruno Prueba")

    def test_correo_y_usuario_unicos(self):
        """No pueden existir dos usuarios con el mismo nombre de usuario."""
        f.estudiante("repetido")
        with self.assertRaises((IntegrityError, ValidationError)):
            Usuario.objects.create_user("repetido", "otro@prueba.test", "x", nombre="A", apellido="B")

    def test_correo_obligatorio(self):
        """El correo electrónico es obligatorio al crear usuarios."""
        with self.assertRaises(ValueError):
            Usuario.objects.create_user("sin.correo", "", "x", nombre="A", apellido="B")


class AutenticacionTests(TestCase):
    def setUp(self):
        self.est = f.estudiante("ana.login")
        self.admin = f.administrador()

    def test_admin_es_dirigido_a_su_panel(self):
        """El administrador llega al panel administrativo al iniciar sesión."""
        r = self.client.post(reverse("accounts:login"), {"username": "admin.prueba", "password": f.CLAVE}, follow=True)
        self.assertEqual(r.redirect_chain[-1][0], reverse("academics:panel"))

    def test_usuario_inexistente_no_inicia_sesion(self):
        """Un usuario inexistente recibe el mismo mensaje genérico de error."""
        r = self.client.post(reverse("accounts:login"), {"username": "nadie", "password": "x"})
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(r, "Usuario o contraseña incorrectos")

    def test_usuario_inactivo_no_inicia_sesion(self):
        """Una cuenta desactivada no puede iniciar sesión."""
        self.est.usuario.is_active = False
        self.est.usuario.save()
        self.client.post(reverse("accounts:login"), {"username": "ana.login", "password": f.CLAVE})
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_cerrar_sesion(self):
        """Cerrar sesión elimina la autenticación."""
        self.client.force_login(self.est.usuario)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_anonimo_es_enviado_al_login(self):
        """Las páginas protegidas exigen iniciar sesión."""
        for nombre in ("enrollments:panel", "academics:panel", "quality_lab:laboratorio"):
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertTrue(r["Location"].startswith(reverse("accounts:login")))


class PermisosTests(TestCase):
    def setUp(self):
        self.est = f.estudiante("ana.permisos")
        self.admin = f.administrador()
        f.periodo()

    def test_estudiante_no_accede_a_paginas_administrativas(self):
        """Un estudiante recibe 403 en todas las secciones administrativas."""
        self.client.force_login(self.est.usuario)
        for nombre in ("academics:panel", "academics:asignaturas", "academics:periodos", "academics:secciones",
                       "academics:docentes", "academics:cupos", "admin_estudiantes",
                       "matriculas_admin:admin_matriculas", "quality_lab:laboratorio",
                       "quality_lab:verificacion", "quality_lab:validacion"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)

    def test_estudiante_no_puede_ejecutar_pruebas(self):
        """Un estudiante no puede lanzar la ejecución de pruebas."""
        self.client.force_login(self.est.usuario)
        self.assertEqual(self.client.post(reverse("quality_lab:ejecutar")).status_code, 403)

    def test_admin_no_usa_funciones_de_estudiante(self):
        """Un administrador sin perfil estudiantil no puede matricularse."""
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("enrollments:matricula")).status_code, 403)
        self.assertEqual(self.client.post(reverse("enrollments:confirmar"), {"secciones": [1]}).status_code, 403)
