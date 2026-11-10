# CampusFlow — Sistema de Matrícula Académica

Aplicación web local para matrícula universitaria, construida para demostrar en una exposición la diferencia entre **verificación** y **validación** del software.

- **Verificación** — *¿estamos construyendo correctamente el producto?* El sistema cumple sus reglas, y las pruebas automatizadas lo comprueban.
- **Validación** — *¿estamos construyendo el producto correcto?* El sistema resuelve lo que el estudiante necesita. Eso solo se averigua preguntando a usuarios reales.

Todo funciona en `localhost`, sin internet una vez instaladas las dependencias, con Django + SQLite.

---

## 1. Requisitos del sistema

- Python **3.12 o superior** (probado con Python 3.14 y Django 6.0.10).
- `pip` y el módulo `venv` (incluidos en Python).
- Un navegador moderno (Chrome, Firefox, Edge).

## 2. Crear el entorno virtual

Desde la carpeta del proyecto:

```bash
python -m venv .venv
```

Activarlo:

```bash
# Linux / macOS (bash, zsh)
source .venv/bin/activate
# Linux (fish)
source .venv/bin/activate.fish
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

La configuración es opcional. Para cambiarla, copia `.env.example` como `.env`; sin ese archivo se usan los valores por defecto para desarrollo local.

## 4. Ejecutar migraciones

```bash
python manage.py migrate
```

Crea `db.sqlite3` con las tablas en español: `usuarios`, `estudiantes`, `carreras`, `asignaturas`, `periodos_academicos`, `secciones`, `horarios`, `docentes`, `matriculas`, `detalles_matricula`, `evaluaciones_experiencia` y `configuracion_demo`. Las tablas internas de Django (`django_session`, `auth_permission`…) conservan su nombre original.

## 5. Cargar los datos iniciales

```bash
python manage.py cargar_demo
```

Carga 1 administrador, 3 estudiantes, 2 carreras, 12 asignaturas (una inactiva), 6 docentes, 17 secciones, un período activo y uno cerrado, y algunas matrículas. Las fechas del período activo se calculan a partir del día de carga, así que la matrícula queda abierta 30 días. Si la base ya tiene datos, el comando no hace nada.

## 6. Iniciar el servidor

```bash
python manage.py runserver
```

Abrir **http://127.0.0.1:8000**

## 7. Cuentas de prueba

> Estas credenciales son ficticias y **solo sirven para desarrollo local**. No uses esta configuración en un servidor público.

| Usuario       | Contraseña         | Rol           | Situación en la demo |
|---------------|--------------------|---------------|----------------------|
| `admin`       | `CampusAdmin2026!` | Administrador | Gestiona la oferta y abre el Laboratorio VyV |
| `ana.torres`  | `Estudiante2026!`  | Estudiante    | ISW, 3.er semestre. Ya tiene Matemática Discreta (A) |
| `bruno.mena`  | `Estudiante2026!`  | Estudiante    | ISW. Tiene Base de Datos I (A) e Ingeniería de Requisitos (A) |
| `carla.rios`  | `Estudiante2026!`  | Estudiante    | CDA. Tiene Base de Datos I (A) y Álgebra Lineal (A) |

### Situaciones preparadas para la demostración (período activo)

| Situación | Cómo provocarla con `ana.torres` |
|---|---|
| Matrícula exitosa | Fundamentos de Programación **A** (Lun/Mié 07:00–09:00) y Verificación y Validación **A** (Mié 09:00–12:00). Se tocan a las 09:00, pero no se cruzan. |
| Asignatura duplicada | Matemática Discreta **B** (Ana ya tiene la A). |
| Cupo agotado | Base de Datos I **A**: capacidad 2, ocupada por Bruno y Carla. |
| Cruce de horarios | Programación Orientada a Objetos **A** (Lun/Mié 08:00–10:00) junto con Fundamentos de Programación A, o Interacción Humano-Computador **A** (Jue 07:30–09:30) contra su Matemática Discreta A. |
| Necesidad de usabilidad | En la **Versión A** no hay vista semanal: armar un horario sin cruces obliga a leer bloques de texto. |

## 8. Ejecutar las pruebas

Suite completa (unitarias, de integración y casos V01–V09):

```bash
python manage.py test
```

Solo los casos del laboratorio, guardando el reporte que muestra la web:

```bash
python manage.py ejecutar_vyv              # suite completa + reporte
python manage.py ejecutar_vyv --solo-casos # solo V01–V09 (unos 3 s)
```

Las pruebas usan una base de datos **SQLite en memoria** que Django crea y destruye en cada ejecución. `db.sqlite3` no se modifica. El laboratorio lo muestra contando registros de la base principal antes y después de ejecutar.

## 9. Restaurar la demostración

Antes de cada ensayo o de la exposición:

```bash
python manage.py reset_demo        # pide escribir RESTAURAR
python manage.py reset_demo --si   # sin pregunta
```

- Borra y vuelve a crear asignaturas, períodos, secciones, docentes, matrículas y las cuentas demo, y deja la experiencia en Versión A.
- **Conserva** las evaluaciones de participantes, que son evidencia real, y las cuentas administrativas creadas fuera de la demo. Para borrar también las evaluaciones, agrega `--incluir-evaluaciones`.
- Protecciones: se niega a ejecutarse si `DEBUG` está desactivado, si `CAMPUSFLOW_ENTORNO` no es `local` o si la base de datos no es un archivo SQLite dentro de la carpeta del proyecto. Sin terminal interactiva exige `--si`.

---

## Funcionalidades

**Estudiante**: panel con información académica y plazo, oferta filtrable por nombre y carrera (horarios, docente y cupos reales), matrícula, comprobante, *Mis asignaturas* con retiro y un formulario para evaluar la experiencia.

**Administrador**: panel con métricas, CRUD de asignaturas (con desactivación), períodos, docentes y secciones con horarios, disponibilidad de cupos, estudiantes, matrículas y el **Laboratorio de Calidad — VyV**.

### Reglas de negocio (`enrollments/services.py`)

| Regla | Dónde se aplica |
|---|---|
| R1 Sin asignatura duplicada en el período | Servicio + restricción única parcial en `detalles_matricula` |
| R2 Sin matricular secciones sin cupo | Servicio. Los cupos se cuentan con los detalles `inscrita`, y se vuelven a comprobar dentro de la transacción |
| R3 Sin cruces de horario | Servicio (contra lo ya inscrito y dentro de la selección) |
| R4 Al menos una asignatura | Navegador + servicio |
| R5 Solo dentro del período habilitado | Período `activo` y fecha actual ≤ fecha límite |
| R6 Validación en frontend y backend | HTML5/JS en formularios + formularios y servicios Django |
| R7–R8 Persistencia real y cupos desde registros | ORM sobre SQLite y conteo con `Count` |
| R9 Atomicidad | `transaction.atomic()`: si una regla falla, no se guarda nada |
| R10 Solo la matrícula propia | Las consultas se filtran por el estudiante de la sesión (404 si es ajena) y las páginas por rol (403) |

**Cancelación y recuperación de cupos**

- Se puede retirar una asignatura mientras el período esté activo y no haya vencido la fecha límite de matrícula.
- El retiro no borra el registro: el detalle pasa a `retirada` con su fecha.
- El cupo se libera de inmediato, porque solo cuentan los detalles `inscrita`.
- Si se retiran todas las asignaturas, la matrícula queda «sin asignaturas vigentes» y vuelve a «activa» si el estudiante se matricula de nuevo.

### Laboratorio de Calidad — VyV

- **Verificación** (`/administracion/laboratorio/verificacion/`): los botones ejecutan `manage.py test` en un proceso aparte con un *test runner* propio (`quality_lab/runner.py`). Ese runner registra cada caso V01–V09 con los datos que usó y el resultado que obtuvo, y guarda el reporte en `var/reporte_verificacion.json`. Mientras no se ejecuten las pruebas, ningún caso aparece como aprobado.
- **Validación** (`/administracion/laboratorio/validacion/`) contiene:
  - la necesidad investigada;
  - la comparación entre la Versión A y la Versión B;
  - el selector de versión;
  - el resumen de las evaluaciones.

  Las respuestas se presentan como opiniones de participantes: el sistema no declara validada ninguna versión.
- La barra **Demostración VyV**, visible solo con `CAMPUSFLOW_MODO_DEMO=true`, aparece en la página de matrícula. Permite:
  - cambiar entre la Versión A y la B;
  - desactivar la validación del navegador, para comprobar que el backend también rechaza las selecciones inválidas;
  - abrir el formulario de evaluación.

## Estructura

```
campusflow/        Configuración, URLs, fábricas de datos de prueba
accounts/          Usuario (rol), Estudiante, inicio de sesión, permisos por rol
academics/         Carreras, docentes, asignaturas, períodos, secciones, horarios (gestión admin)
enrollments/       Matrícula, detalle, servicios con las reglas, vistas del estudiante
quality_lab/       Laboratorio VyV, runner de pruebas, evaluaciones, comandos de demo
templates/ static/ Interfaz (HTML, CSS y JS propios, sin frameworks externos)
```

Comandos propios: `cargar_demo`, `reset_demo` y `ejecutar_vyv`.

Guion de la exposición: [`GUIA_EXPOSICION.md`](GUIA_EXPOSICION.md).
