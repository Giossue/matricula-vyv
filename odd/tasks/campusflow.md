# CampusFlow — Sistema de Matrícula Académica (demo VyV)

Objetivo: app Django local de matrícula con Laboratorio de Calidad (verificación + validación). Sin git (carpeta no es repositorio; el usuario no quiere commits). Runner: `python manage.py test`.

## Specs

- S1 Stack: Django + SQLite (ORM), Templates/HTML/CSS/JS propios, auth de Django, TestCase, venv + requirements.txt. Sin servicios externos.
- S2 Diseño: fondo blanco/gris claro, azul marino/azul universitario, verde éxito, rojo error, sidebar en escritorio, responsive, sin emojis ni degradados morados.
- S3 Roles: Administrador (dashboard, CRUD asignaturas/períodos/secciones/horarios/docentes/cupos, estudiantes, matrículas, cupos) y Estudiante (info académica, oferta filtrable por nombre y carrera, seleccionar, confirmar, mis asignaturas, retirar). Estudiante sin acceso admin.
- S4 Modelos: Usuario, Estudiante, Carrera, Asignatura, Período académico, Sección, Horario, Matrícula, Detalle de matrícula (tablas/columnas en español).
- S5 Reglas 1–10 del enunciado + reglas de cancelación y recuperación de cupos.
- S6 Laboratorio VyV: Verificación V01–V09 ejecutadas realmente con el test runner de Django sobre BD aislada; Validación con Versión A / Versión B, selector solo en demo, formulario de evaluación guardado en BD, Versión B no presentada como validada.
- S7 Datos: comando de carga reproducible (1 admin, 3 estudiantes, 2 carreras, 8–12 asignaturas, sección llena, cruces, período activo, matrículas existentes) y `reset_demo` protegido.
- S8 Docs: README (9 pasos), GUIA_EXPOSICION.md (~10 min, 4 escenas), .gitignore, .env.example.

## Tasks

- [x] T1 S1,S4 estructura, settings, modelos, migraciones — inline — `migrate` OK, tablas en español
- [x] T2 S3,S5 auth, roles, servicios de matrícula, vistas — inline — cubierto por pruebas
- [x] T3 S2 interfaz — inline — revisada con capturas headless (escritorio y móvil)
- [x] T4 S6 laboratorio verificación + validación — inline — `ejecutar_vyv` 82/82; mutación de cruces → V06 fallido
- [x] T5 S7 comandos de datos — inline — `cargar_demo`, `reset_demo` (protecciones probadas)
- [x] T6 S1,S5 pruebas — inline — `python manage.py test`: 82 OK
- [x] T7 S8 documentación — inline — README.md, GUIA_EXPOSICION.md
- [x] T8 verificación independiente (riesgo ítem 2: auth/permisos) — delegada — autorización, reglas, reset_demo y guía: pasa

## Log

- L1 (2026-11-09) Petición original: "PROYECTO: Sistema de Matrícula Universitaria — Demostración de Verificación y Validación" (enunciado completo en la conversación).
- L2 Restricciones del usuario: no commits/push; venv en la carpeta; nombres de BD en español; no iniciar servidores (verificar con `check`, tests y cliente de pruebas).
- L3 (2026-11-09) Evidencia: 82 pruebas OK; hash de db.sqlite3 idéntico antes/después de ejecutar el laboratorio; mutación (cruces desactivados) hace fallar V06 con "La matrícula fue ACEPTADA"; con el chequeo de cupos desactivado V05 sigue aprobando porque la re-validación dentro de la transacción lo atrapa (defensa en profundidad).
- L4 (2026-11-09) Verificador independiente: 1 blocker de documentación (la guía decía «una vez por versión», que no se impone) → corregido el texto; advisory de entero gigante → 500 corregido (`_normalizar_ids` acota a 2**63) con prueba. Suite 82 OK.
