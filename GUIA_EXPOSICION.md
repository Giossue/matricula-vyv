# Guía de exposición — Verificación frente a validación en una app de matrícula estudiantil

**Duración estimada:** 10 minutos, más preguntas.
**Sistema:** MatriculaVyV — Sistema de Matrícula Académica (local).

---

## Preparación (antes de entrar al aula)

1. Restaurar los datos y dejar la experiencia en Versión A:
   ```bash
   python manage.py reset_demo --si
   ```
2. Dejar un reporte de pruebas reciente, por si el proyector o el equipo van lentos:
   ```bash
   python manage.py ejecutar_vyv
   ```
3. Iniciar el servidor (`python manage.py runserver`) y abrir dos ventanas del navegador:
   - **Ventana 1** (normal): `ana.torres` / `Estudiante2026!`, el estudiante de la demo.
   - **Ventana 2** (incógnito u otro navegador): `admin` / `CampusAdmin2026!`, para el laboratorio y para cambiar de versión.
   - Para la escena 3, el compañero entrará como `bruno.mena` / `Estudiante2026!` (puede ser en la ventana 1 después de cerrar la sesión de Ana).
4. Aumentar el zoom del navegador al 110–125 % para el proyector.

| Escena | Tiempo | Pregunta que responde |
|---|---|---|
| 1. Presentación del sistema | 1:30 | ¿Qué hace MatriculaVyV? |
| 2. Verificación | 4:00 | ¿Construimos correctamente el producto? |
| 3. Validación | 3:30 | ¿Construimos el producto correcto? |
| 4. Conclusión | 1:00 | ¿Por qué hacen falta las dos? |

---

## Escena 1 — Presentación del sistema (≈ 1:30)

**Ventana 1, como Ana.**

1. Mostrar **Inicio**: código estudiantil, carrera, semestre, período activo, días que quedan de matrícula y la asignatura que ya tiene (Matemática Discreta, paralelo A).
2. Abrir **Oferta académica**. Filtrar por nombre (`program`) y luego por carrera.

> **Decir:** «MatriculaVyV permite consultar asignaturas, horarios, docentes y cupos, matricularse y retirar materias. Los requisitos principales son: no matricular dos veces la misma asignatura, no superar los cupos, no cruzar horarios, matricular solo dentro del plazo y guardar la matrícula de forma completa o no guardarla.»

Señalar que los cupos («2/2 ocupados», «0/30»…) no están escritos en la página: se calculan contando las matrículas guardadas en la base de datos.

---

## Escena 2 — Verificación (≈ 4:00)

> **Frase guía:** «Estamos comprobando que el sistema cumple las reglas establecidas. Esto es verificación.»

### 2.1 Matrícula correcta (Ventana 1, Ana)
1. Ir a **Matricularme** (Versión A).
2. Marcar **Fundamentos de Programación — Paralelo A** (Lun/Mié 07:00–09:00) y **Verificación y Validación de Software — Paralelo A** (Mié 09:00–12:00).
3. Pulsar **Confirmar matrícula**. Se abre el comprobante con ambas materias en estado *Inscrita*.
4. Comentario opcional: «Una termina a las 09:00 y la otra empieza a las 09:00. El sistema no lo considera un cruce, y eso también está especificado y probado.»

### 2.2 Cupo agotado
1. Volver a **Matricularme**. **Base de Datos I — Paralelo A** aparece como *Sin cupos (2/2)* y no se puede marcar. Es la validación del navegador.
2. Para demostrar que el **backend** también lo impide, pulsar en la barra de demostración **Validación del navegador: activa**. Pasa a *desactivada*.
3. Marcar Base de Datos I A y confirmar. El servidor responde: *«… no tiene cupos disponibles (2/2 ocupados)»* con la regla `CUPO_AGOTADO`. No se guardó nada.

> «La validación del navegador es una comodidad. La regla real vive en el servidor, y eso es lo que estamos verificando.»

### 2.3 Cruce de horarios
1. Con la validación del navegador aún desactivada, marcar **Programación Orientada a Objetos — Paralelo A** (Lun/Mié 08:00–10:00).
2. Confirmar. El sistema rechaza: *«… se cruza el Lunes 08:00–10:00 con Fundamentos de Programación (paralelo A), ya inscrita.»* (`CRUCE_HORARIO`).
3. Opcional, para mostrar que la operación es **atómica**: marcar a la vez Programación OO A (cruza) y Cálculo Diferencial **B** (válida). Al confirmar no se guarda **ninguna** de las dos.
4. Opcional, asignatura duplicada: marcar **Matemática Discreta — Paralelo B** → `ASIGNATURA_DUPLICADA`.
5. Volver a activar la validación del navegador.

### 2.4 La matrícula está en la base de datos (Ventana 2, admin)
1. **Matrículas** → buscar «Ana» → **Ver**: aparecen las asignaturas registradas y su hora.
2. Alternativa técnica, en una terminal:
   ```bash
   python manage.py shell -c "from enrollments.models import DetalleMatricula as D; print(list(D.objects.filter(matricula__estudiante__usuario__nombre_usuario='ana.torres').values_list('seccion__asignatura__nombre','estado')))"
   ```
3. **Disponibilidad de cupos**: la ocupación de Fundamentos de Programación A subió en 1.

### 2.5 Pruebas automatizadas reales (Ventana 2)
1. **Laboratorio VyV → Abrir verificación**.
2. Pulsar **Solo V01–V09** (unos 3 segundos) o **Suite completa** (unos 25 segundos).
3. Abrir un par de casos (V05 y V06) y leer: *objetivo, datos utilizados, resultado esperado, resultado obtenido, estado y explicación*.
4. Señalar el recuadro **Aislamiento de la base de datos principal**: los registros de `db.sqlite3` son los mismos antes y después. Las pruebas usaron una base temporal en memoria.

> «Ningún “Aprobado” está escrito a mano. Si mañana alguien rompe la regla de cruces, V06 aparecerá como fallido con el resultado real: *“La matrícula fue ACEPTADA”*.»

---

## Escena 3 — Validación (≈ 3:30)

> **Frase guía:** «Aunque la primera versión funciona técnicamente, necesitamos comprobar si responde a las necesidades reales del estudiante. Esto es validación.»

### 3.1 Versión A con un compañero
1. En la Ventana 2 (admin) abrir **Laboratorio VyV → Abrir validación** y confirmar que está activa la **Versión A**. Mostrar el recuadro «Necesidad investigada».
2. En la Ventana 1, cerrar la sesión de Ana e invitar a un compañero a ingresar como **`bruno.mena`**.
3. Darle esta **tarea**:
   > «Ya tienes Base de Datos I (Mar/Jue 09–11) e Ingeniería de Requisitos (Lun 14–17). Agrega **tres asignaturas más** sin que se crucen, y **antes de confirmar** dime cómo queda tu semana el miércoles.»
4. Observar sin ayudar. Con la Versión A tiene que leer los horarios como texto, paralelo por paralelo, y recordar o anotar los bloques. Si se equivoca, el cruce aparece **después** de confirmar.
5. Preguntarle:
   - «¿Fue fácil elegir?»
   - «¿Pudiste saber cómo quedaba tu semana antes de confirmar?»
   - «¿La información te alcanzó para decidir?»

### 3.2 Versión B
1. Pulsar **Versión B** en la barra de demostración (en su ventana o en la del admin).
2. Pedirle que repita la tarea. Ahora ve:
   - el **calendario semanal** con lo que ya tiene y lo que va eligiendo;
   - avisos como *«Se cruzaría con …»* antes de marcar;
   - el **resumen** de materias y créditos;
   - un paso **Revisar y confirmar** donde el servidor comprueba la selección antes de guardar.
3. Pedirle que **compare** ambas experiencias en voz alta.

### 3.3 Registrar la evaluación
1. El compañero pulsa **Evaluar esta versión** y responde el formulario: una vez después de la Versión A y otra después de la B. El sistema no limita los envíos (varios participantes pueden compartir la cuenta demo), así que pídele que envíe cada formulario una sola vez para no inflar los promedios.
2. En la Ventana 2 (Laboratorio de Validación), mostrar el resumen por versión y los comentarios.

> «Estas respuestas son **opiniones de participantes**. El sistema no puede decidir solo si la Versión B es “la correcta”. Con una o dos personas no podemos declararla validada: hace falta evaluarla con más usuarios reales y analizar los resultados.»

Señalar que el estado de la Versión B dice «Pendiente» o «En evaluación», nunca «Validada».

---

## Escena 4 — Conclusión (≈ 1:00)

- **Qué se comprobó con verificación:** login, permisos por rol, persistencia, duplicados, cupos, cruces, atomicidad y recuperación de cupos. Lo comprobaron pruebas automatizadas reales (V01–V09 y el resto de la suite).
- **Qué necesidad se investigó con validación:** planificar la semana **antes** de confirmar la matrícula.
- **Qué cambios se propusieron:** la Versión B, con calendario semanal, avisos de cruce, resumen y confirmación en dos pasos. Usa el mismo backend y las mismas reglas.
- **Por qué hacen falta ambas:** un sistema puede pasar todas las pruebas (verificado) y aun así no servir bien a quien lo usa (no validado). Y una idea muy cómoda para el usuario no sirve si no respeta las reglas.

### Preguntas para el público
1. «Si la Versión A pasa las 9 pruebas, ¿está lista para producción? ¿Por qué sí o por qué no?»
2. «¿Qué prueba automatizada escribirían para la Versión B? ¿Esa prueba verificaría o validaría?»
3. «¿Cuántas personas, y de qué perfil, deberían evaluar la Versión B para que confiemos en el resultado?»
4. «¿Qué otra necesidad real de un estudiante creen que este sistema todavía no resuelve?»

---

## Plan B, si algo falla en vivo

| Problema | Qué hacer |
|---|---|
| Los datos quedaron alterados por un ensayo | `python manage.py reset_demo --si` y volver a iniciar sesión. |
| La suite tarda demasiado | Usar **Solo V01–V09**, o mostrar el último reporte guardado con `ejecutar_vyv`. |
| «La matrícula no está habilitada» | El período venció (más de 30 días desde la carga): ejecutar `reset_demo`. |
| No se ve la barra de demostración | Revisar que `.env` no tenga `CAMPUSFLOW_MODO_DEMO=false`. |
