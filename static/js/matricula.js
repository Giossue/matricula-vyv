/* Selección de asignaturas en la página de matrícula.
 *
 * Versión A y B comparten:
 *   - un paralelo por asignatura,
 *   - no se puede enviar sin seleccionar al menos una asignatura.
 * La Versión B agrega: calendario semanal en vivo, avisos de cruce,
 * resumen de créditos y un paso de revisión que consulta al backend.
 *
 * Estas comprobaciones son de comodidad: el backend vuelve a validar todo.
 * Si la demo desactiva la validación del navegador (data-sin-validacion),
 * nada de esto bloquea el envío y responde solo el servidor.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-form-matricula]");
  if (!form) return;

  var version = form.getAttribute("data-version");
  var sinValidacion = form.hasAttribute("data-sin-validacion");
  var casillas = Array.prototype.slice.call(form.querySelectorAll("input[name=secciones]"));
  var errorEnvio = form.querySelector("[data-error-envio]");

  var oferta = leerJSON("datos-oferta");
  var vigentes = leerJSON("datos-vigentes");
  var porId = {};
  oferta.forEach(function (s) { porId[s.id] = s; });

  function leerJSON(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : [];
  }

  function seleccionadas() {
    return casillas.filter(function (c) { return c.checked; });
  }

  function mostrarError(texto) {
    if (!errorEnvio) return;
    errorEnvio.hidden = !texto;
    errorEnvio.textContent = texto || "";
  }

  // ---------- Común a ambas versiones ----------
  casillas.forEach(function (casilla) {
    casilla.addEventListener("change", function () {
      var opcion = casilla.closest("[data-opcion]");
      if (casilla.checked && !sinValidacion) {
        // Un solo paralelo por asignatura.
        var asignatura = opcion.getAttribute("data-asignatura");
        casillas.forEach(function (otra) {
          var o = otra.closest("[data-opcion]");
          if (otra !== casilla && o.getAttribute("data-asignatura") === asignatura) {
            otra.checked = false;
            o.classList.remove("is-selected");
          }
        });
      }
      opcion.classList.toggle("is-selected", casilla.checked);
      mostrarError("");
      actualizar();
    });
  });

  function actualizarContador() {
    var contador = form.querySelector("[data-contador]");
    if (!contador) return;
    var n = seleccionadas().length;
    contador.textContent = n === 1 ? "1 asignatura seleccionada" : n + " asignaturas seleccionadas";
  }

  form.addEventListener("submit", function (ev) {
    if (sinValidacion) return;
    if (seleccionadas().length === 0) {
      ev.preventDefault();
      mostrarError("Selecciona al menos una asignatura antes de confirmar.");
    }
  });

  // ---------- Solo Versión B ----------
  function seCruzan(a, b) {
    var m = window.CampusCalendario.minutos;
    return a.dia === b.dia && m(a.inicio) < m(b.fin) && m(b.inicio) < m(a.fin);
  }

  function primerCruce(seccion, otras) {
    for (var i = 0; i < otras.length; i++) {
      var otra = otras[i];
      if (otra.id === seccion.id) continue;
      for (var x = 0; x < seccion.horarios.length; x++) {
        for (var y = 0; y < otra.horarios.length; y++) {
          if (seCruzan(seccion.horarios[x], otra.horarios[y])) {
            return { con: otra, bloque: seccion.horarios[x] };
          }
        }
      }
    }
    return null;
  }

  function analizar() {
    var elegidas = seleccionadas().map(function (c) { return porId[c.value]; }).filter(Boolean);
    var conflictos = {};
    elegidas.forEach(function (s, i) {
      var cruce = primerCruce(s, vigentes) || primerCruce(s, elegidas.slice(0, i));
      if (cruce) conflictos[s.id] = cruce;
    });
    return { elegidas: elegidas, conflictos: conflictos };
  }

  function textoCruce(s, cruce) {
    return s.asignatura + " (P. " + s.paralelo + ") se cruza con " + cruce.con.asignatura +
      " (P. " + cruce.con.paralelo + ") el " + cruce.bloque.texto + ".";
  }

  function actualizarB() {
    var estado = analizar();
    var elegidasIds = estado.elegidas.map(function (s) { return s.id; });

    // Marcas en cada opción: cruces de lo elegido y avisos preventivos en lo no elegido.
    casillas.forEach(function (c) {
      var opcion = c.closest("[data-opcion]");
      var aviso = opcion.querySelector("[data-aviso]");
      var s = porId[c.value];
      var texto = "";
      opcion.classList.remove("is-conflict");
      if (s && c.checked && estado.conflictos[s.id]) {
        opcion.classList.add("is-conflict");
        texto = "Cruce: " + textoCruce(s, estado.conflictos[s.id]);
      } else if (s && !c.checked && !c.disabled) {
        var otras = vigentes.concat(estado.elegidas.filter(function (e) { return e.asignatura_id !== s.asignatura_id; }));
        var cruce = primerCruce(s, otras);
        if (cruce) texto = "Se cruzaría con " + cruce.con.asignatura + " (" + cruce.bloque.texto + ").";
      }
      if (aviso) { aviso.hidden = !texto; aviso.textContent = texto; }
    });

    // Resumen.
    var lista = form.querySelector("[data-resumen]");
    lista.innerHTML = "";
    if (!estado.elegidas.length) {
      lista.innerHTML = '<li class="muted">Aún no has seleccionado asignaturas.</li>';
    }
    var creditos = 0;
    estado.elegidas.forEach(function (s) {
      creditos += s.creditos;
      var li = document.createElement("li");
      if (estado.conflictos[s.id]) li.className = "conflicto";
      var a = document.createElement("span"); a.textContent = s.asignatura + " · P. " + s.paralelo;
      var b = document.createElement("span"); b.textContent = s.creditos + " cr.";
      li.appendChild(a); li.appendChild(b);
      lista.appendChild(li);
    });
    form.querySelector("[data-creditos]").textContent = creditos;
    var totalEl = form.querySelector("[data-creditos-total]");
    var yaMatriculados = vigentes.reduce(function (t, s) { return t + s.creditos; }, 0);
    totalEl.textContent = yaMatriculados + creditos;

    var avisos = form.querySelector("[data-avisos]");
    var ids = Object.keys(estado.conflictos);
    avisos.innerHTML = "";
    if (ids.length) {
      var caja = document.createElement("div");
      caja.className = "alert alert-error";
      var ul = document.createElement("ul");
      ids.forEach(function (id) {
        var li = document.createElement("li");
        li.textContent = textoCruce(porId[id], estado.conflictos[id]);
        ul.appendChild(li);
      });
      var cuerpo = document.createElement("div");
      var titulo = document.createElement("strong");
      titulo.textContent = "Hay cruces de horario. Cambia de paralelo o quita una asignatura.";
      cuerpo.appendChild(titulo); cuerpo.appendChild(ul);
      caja.appendChild(cuerpo);
      avisos.appendChild(caja);
    }

    // Calendario.
    var cal = form.querySelector("[data-calendario]");
    var bloques = window.CampusCalendario.bloquesDe(vigentes, "vigente");
    estado.elegidas.forEach(function (s) {
      bloques = bloques.concat(window.CampusCalendario.bloquesDe([s], estado.conflictos[s.id] ? "conflicto" : "seleccion"));
    });
    window.CampusCalendario.render(cal, bloques);
    return { estado: estado, ids: elegidasIds };
  }

  function actualizar() {
    actualizarContador();
    if (version === "B") actualizarB();
  }

  if (version === "B") {
    var dialogo = form.querySelector("[data-dialogo-revision]");
    var botonConfirmar = form.querySelector("[data-confirmar-final]");

    form.querySelector("[data-abrir-revision]").addEventListener("click", function () {
      var r = actualizarB();
      if (!sinValidacion) {
        if (!r.ids.length) { mostrarError("Selecciona al menos una asignatura para continuar."); return; }
        if (Object.keys(r.estado.conflictos).length) { mostrarError("Resuelve los cruces de horario antes de confirmar."); return; }
      }
      var lista = dialogo.querySelector("[data-revision-lista]");
      lista.innerHTML = "";
      r.estado.elegidas.forEach(function (s) {
        var li = document.createElement("li");
        var a = document.createElement("span");
        a.textContent = s.asignatura + " · P. " + s.paralelo + " · " + s.horarios.map(function (h) { return h.texto; }).join("; ");
        var b = document.createElement("span"); b.textContent = s.creditos + " cr.";
        li.appendChild(a); li.appendChild(b); lista.appendChild(li);
      });
      if (!r.estado.elegidas.length) lista.innerHTML = '<li class="muted">Sin asignaturas seleccionadas.</li>';

      var zona = dialogo.querySelector("[data-revision-servidor]");
      zona.innerHTML = '<div class="alert alert-info"><div>Comprobando con el sistema…</div></div>';
      botonConfirmar.disabled = !sinValidacion;
      form.querySelector("[data-paso-3]").classList.add("on");
      dialogo.showModal();

      fetch(form.getAttribute("data-url-validar"), {
        method: "POST", body: new FormData(form), credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (resp) { return resp.json(); })
        .then(function (datos) {
          zona.innerHTML = "";
          var caja = document.createElement("div");
          if (datos.valida) {
            caja.className = "alert alert-success";
            caja.textContent = "El sistema comprobó tu selección: cumple todas las reglas (cupos, cruces y duplicados). Aún no se ha guardado.";
            botonConfirmar.disabled = false;
          } else {
            caja.className = "alert alert-error";
            var ul = document.createElement("ul");
            datos.incidencias.forEach(function (i) {
              var li = document.createElement("li"); li.textContent = i.mensaje; ul.appendChild(li);
            });
            var t = document.createElement("strong"); t.textContent = "El sistema encontró problemas:";
            var cuerpo = document.createElement("div"); cuerpo.appendChild(t); cuerpo.appendChild(ul);
            caja.appendChild(cuerpo);
            botonConfirmar.disabled = !sinValidacion;
          }
          zona.appendChild(caja);
        })
        .catch(function () {
          zona.innerHTML = '<div class="alert alert-warning"><div>No se pudo comprobar ahora. Puedes confirmar: el servidor validará igualmente.</div></div>';
          botonConfirmar.disabled = false;
        });
    });

    form.querySelector("[data-cerrar-revision]").addEventListener("click", function () {
      dialogo.close();
      form.querySelector("[data-paso-3]").classList.remove("on");
    });
  }

  actualizar();
})();
