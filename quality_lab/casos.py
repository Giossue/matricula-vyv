"""Catálogo de casos del Laboratorio de Verificación.

Describe qué comprueba cada caso. El resultado (aprobado/fallido y el
resultado obtenido) NO está aquí: lo produce la ejecución real de las pruebas
en quality_lab/tests/test_verificacion.py.
"""

CASOS = {
    "V01": {
        "titulo": "Inicio de sesión correcto",
        "objetivo": "Comprobar que un usuario registrado puede autenticarse y llega a su panel.",
        "datos": "Usuario estudiante con contraseña válida.",
        "esperado": "Redirección al panel del estudiante y sesión autenticada.",
        "explicacion": "Si las credenciales son correctas, Django crea la sesión y el sistema envía a cada rol a su panel.",
    },
    "V02": {
        "titulo": "Rechazo de credenciales incorrectas",
        "objetivo": "Comprobar que una contraseña equivocada no permite entrar.",
        "datos": "Usuario existente con contraseña incorrecta.",
        "esperado": "Permanece en el formulario, se muestra un mensaje de error y no hay sesión.",
        "explicacion": "La contraseña se compara contra el hash almacenado; nunca se guarda en texto plano.",
    },
    "V03": {
        "titulo": "Registro exitoso de matrícula",
        "objetivo": "Comprobar que una selección válida queda registrada.",
        "datos": "Estudiante sin matrícula y una sección con cupos y sin cruces.",
        "esperado": "Se crea la matrícula con un detalle en estado «inscrita».",
        "explicacion": "Cuando todas las reglas se cumplen, el servicio guarda matrícula y detalle en una sola transacción.",
    },
    "V04": {
        "titulo": "Bloqueo de asignatura duplicada",
        "objetivo": "Comprobar que no se puede matricular dos veces la misma asignatura en el período.",
        "datos": "Estudiante ya inscrito en una asignatura que intenta otro paralelo de la misma.",
        "esperado": "Rechazo con la regla ASIGNATURA_DUPLICADA y sin registros nuevos.",
        "explicacion": "Lo impide el servicio y, como segunda barrera, una restricción única en la base de datos.",
    },
    "V05": {
        "titulo": "Bloqueo de matrícula sin cupos",
        "objetivo": "Comprobar que no se supera la capacidad máxima de una sección.",
        "datos": "Sección con capacidad 1 ya ocupada por otro estudiante.",
        "esperado": "Rechazo con la regla CUPO_AGOTADO; los inscritos no superan la capacidad.",
        "explicacion": "Los cupos se calculan contando los detalles inscritos reales, no con un contador manual.",
    },
    "V06": {
        "titulo": "Detección de cruce de horarios",
        "objetivo": "Comprobar que no se matriculan dos asignaturas que se dictan a la misma hora.",
        "datos": "Dos secciones el lunes: 07:00–09:00 y 08:00–10:00.",
        "esperado": "Rechazo con la regla CRUCE_HORARIO y ninguna de las dos guardada (atomicidad).",
        "explicacion": "Dos bloques se cruzan si comparten día y uno empieza antes de que el otro termine.",
    },
    "V07": {
        "titulo": "Persistencia correcta de datos",
        "objetivo": "Comprobar que la matrícula realmente se escribe en SQLite.",
        "datos": "Matrícula confirmada desde la interfaz web (cliente de pruebas).",
        "esperado": "Las filas existen al consultar las tablas con SQL directo.",
        "explicacion": "Se lee la tabla detalles_matricula sin pasar por el ORM para confirmar que el dato está almacenado.",
    },
    "V08": {
        "titulo": "Restricción de acceso según rol",
        "objetivo": "Comprobar que un estudiante no entra a funciones administrativas ni a matrículas ajenas.",
        "datos": "Sesión de estudiante que pide el panel administrativo y el comprobante de otro estudiante.",
        "esperado": "HTTP 403 en administración y HTTP 404 en la matrícula ajena.",
        "explicacion": "Cada vista verifica el rol y filtra las matrículas por el estudiante de la sesión.",
    },
    "V09": {
        "titulo": "Recuperación de cupo tras una cancelación válida",
        "objetivo": "Comprobar que retirar una asignatura dentro del plazo libera su cupo.",
        "datos": "Sección llena (1/1); el estudiante inscrito la retira y otro estudiante la toma.",
        "esperado": "El cupo pasa de 0 a 1 tras el retiro y el segundo estudiante se matricula.",
        "explicacion": "El retiro cambia el detalle a «retirada» y deja de contarse como cupo ocupado.",
    },
}
