# CampusFlow — Sistema de Matrícula Académica

Aplicación web local para matrícula universitaria, construida para demostrar en una exposición la diferencia entre **verificación** y **validación** del software.

- **Verificación** — *¿estamos construyendo correctamente el producto?* El sistema cumple sus reglas, y las pruebas automatizadas lo comprueban.
- **Validación** — *¿estamos construyendo el producto correcto?* El sistema resuelve lo que el estudiante necesita. Eso solo se averigua preguntando a usuarios reales.

Todo funciona en `localhost`, sin internet una vez instaladas las dependencias, con Django + SQLite.

---

## Inicio rápido (copiar y pegar)

Requisitos: **Python 3.10 o superior** y `git`.

**Linux / macOS (bash o zsh):**

```bash
git clone https://github.com/Giossue/campusflow.git
cd campusflow
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

**Linux (fish):** igual que arriba, pero activa el entorno con `source .venv/bin/activate.fish`.

**Windows (PowerShell o CMD):** usa directamente el Python del entorno. No hace falta activarlo, así que no aparece el error «la ejecución de scripts está deshabilitada».

```powershell
git clone https://github.com/Giossue/campusflow.git
cd campusflow
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py cargar_demo
.venv\Scripts\python manage.py runserver
```

Si `python` no existe en Windows, prueba con `py` en la tercera línea (`py -m venv .venv`).

Abre **http://127.0.0.1:8000** y entra con:

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `CampusAdmin2026!` | Administrador |
| `ana.torres` | `Estudiante2026!` | Estudiante |

Para usar el sistema otra vez más adelante solo hace falta entrar en la carpeta y ejecutar el servidor: `.venv/bin/python manage.py runserver` en Linux/macOS o `.venv\Scripts\python manage.py runserver` en Windows. Para detener el servidor, pulsa `Ctrl+C`.

En [Cómo usar el sistema](#cómo-usar-el-sistema) está qué hacer con cada cuenta. Abajo está el mismo proceso explicado paso a paso.

---

## 1. Requisitos del sistema

- Python **3.10 o superior**. Usa Django 5.2 LTS y está probado con Python 3.10, 3.11 y 3.14.
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
# Windows (CMD)
.venv\Scripts\activate.bat
```

En Windows PowerShell, el script `Activate.ps1` puede estar bloqueado. En ese caso no actives el entorno: escribe `.venv\Scripts\python` en lugar de `python` en todos los comandos (por ejemplo, `.venv\Scripts\python manage.py migrate`).

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

## Cómo usar el sistema

Al iniciar sesión, cada usuario llega a su propio panel según su rol. La navegación está en el menú lateral; en el móvil se abre con el botón de menú.

### Como estudiante (por ejemplo `ana.torres`)

- **Inicio**: código estudiantil, carrera, semestre, período activo, días que quedan para matricularse y asignaturas inscritas.
- **Oferta académica**: todas las secciones del período con su horario, docente y cupos. Se puede filtrar por nombre y por carrera.
- **Matricularme**:
  1. Marca un paralelo de cada asignatura que quieras.
  2. Pulsa **Confirmar matrícula**.
  3. Si la selección cumple todas las reglas, se abre el **comprobante**.
  4. Si hay cupo agotado, cruce de horario o una asignatura repetida, el sistema explica el motivo y no guarda nada.
- **Mis asignaturas**: lo inscrito en el período, con un botón **Retirar** en cada materia.
  Al retirarla se libera el cupo.
- **Evaluar la experiencia**: formulario de opinión sobre la versión de matrícula que se está usando.

Selecciones para probar con `ana.torres`:

| Qué quieres ver | Qué marcar |
|---|---|
| Matrícula aceptada | Fundamentos de Programación **A** + Verificación y Validación **A** |
| Cupo agotado | Base de Datos I **A** |
| Cruce de horario | Programación Orientada a Objetos **A** junto con Fundamentos de Programación **A** |
| Asignatura repetida | Matemática Discreta **B** (Ana ya tiene la A) |

Para ver los dos últimos rechazos desde el servidor, desactiva primero la validación del navegador en la barra de demostración (ver más abajo). Después de probar, `python manage.py reset_demo --si` deja todo como al principio.

### Como administrador (`admin`)

- **Panel**: métricas generales del período: estudiantes, matrículas, secciones llenas…
- **Asignaturas, Períodos, Secciones y horarios, Docentes**: crear, editar y desactivar. En cada sección se definen el paralelo, el docente, la capacidad y uno o más bloques de horario.
- **Estudiantes, Matrículas y Disponibilidad de cupos**: consulta de solo lectura. En **Matrículas**, el botón **Ver** abre el detalle de cada una.
- **Laboratorio VyV**:
  - **Verificación**:
    - Pulsa **Solo V01–V09** (unos 3 s) o **Suite completa** (unos 25 s).
    - Las pruebas automatizadas se ejecutan de verdad, sobre una base de datos temporal.
    - Cada caso muestra su objetivo, los datos usados, el resultado esperado, el resultado obtenido, el estado y una explicación.
    - El recuadro de aislamiento confirma que `db.sqlite3` no cambió.
  - **Validación**: muestra la necesidad investigada, la comparación entre la Versión A y la B, el selector de versión y el resumen de las evaluaciones de los participantes.

### Barra «Demostración VyV»

Aparece arriba en la página **Matricularme**:

- **Versión A / Versión B**: cambia la experiencia de matrícula para todos los usuarios.
  - **A** es una lista con los horarios en texto.
  - **B** agrega un calendario semanal en vivo, avisos de cruce antes de marcar, un resumen de créditos y un paso **Revisar y confirmar** en el que el servidor comprueba la selección antes de guardar.
- **Validación del navegador: activa / desactivada**: al desactivarla, el navegador deja de bloquear las selecciones inválidas, y así se ve que el servidor también las rechaza.
- **Evaluar esta versión**: abre el formulario de opinión, que se guarda en la base de datos y aparece en el Laboratorio de Validación.

### Problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se encuentra o la versión es menor que 3.10 | Usa `python3` (Linux/macOS) o `py` (Windows), o instala una versión reciente desde python.org. |
| Windows: «la ejecución de scripts está deshabilitada» | No actives el entorno: usa `.venv\Scripts\python` en lugar de `python`, como en el Inicio rápido. |
| `No module named 'django'` | Las dependencias no se instalaron en el entorno. Repite `.venv\Scripts\python -m pip install -r requirements.txt` (Windows) o `.venv/bin/python -m pip install -r requirements.txt` (Linux/macOS). |
| «La matrícula no está habilitada» | El período demo dura 30 días desde la carga. Ejecuta `python manage.py reset_demo --si`. |
| `cargar_demo` no carga nada | La base ya tenía datos. Para empezar de cero, ejecuta `python manage.py reset_demo --si`. |
| El puerto 8000 está ocupado | `python manage.py runserver 8001` y abre http://127.0.0.1:8001 |
| No aparece la barra de demostración | Revisa que `.env` no tenga `CAMPUSFLOW_MODO_DEMO=false`. |

El guion completo de la exposición (unos 10 minutos en 4 escenas) está en [`GUIA_EXPOSICION.md`](GUIA_EXPOSICION.md).

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
