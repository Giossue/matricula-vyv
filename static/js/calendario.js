/* Calendario semanal (lunes a sábado) dibujado con los datos del servidor. */
(function () {
  "use strict";

  var DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

  function minutos(hhmm) {
    var p = hhmm.split(":");
    return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
  }

  function render(contenedor, bloques) {
    var inicio = 7 * 60, fin = 13 * 60;
    bloques.forEach(function (b) {
      inicio = Math.min(inicio, Math.floor(minutos(b.inicio) / 60) * 60);
      fin = Math.max(fin, Math.ceil(minutos(b.fin) / 60) * 60);
    });
    var alturaHora = parseFloat(getComputedStyle(contenedor).getPropertyValue("--hora-h")) || 34;
    var horas = (fin - inicio) / 60;

    contenedor.innerHTML = "";
    contenedor.appendChild(celda("cal-head", ""));
    DIAS.forEach(function (d) { contenedor.appendChild(celda("cal-head", d)); });

    var colHoras = celda("cal-horas", "");
    for (var h = 0; h < horas; h++) {
      var etiqueta = document.createElement("div");
      etiqueta.textContent = String(inicio / 60 + h).padStart(2, "0") + ":00";
      colHoras.appendChild(etiqueta);
    }
    contenedor.appendChild(colHoras);

    for (var dia = 1; dia <= 6; dia++) {
      var col = celda("cal-dia", "");
      col.style.height = (horas * alturaHora) + "px";
      col.setAttribute("aria-label", DIAS[dia - 1]);
      var delDia = carriles(bloques.filter(function (b) { return b.dia === dia; }));
      delDia.forEach(function (b) {
        var el = document.createElement("div");
        el.className = "cal-bloque " + (b.tipo || "");
        // Bloques superpuestos se dibujan lado a lado para que ninguno quede oculto.
        el.style.left = "calc(" + (b.carril / b.carriles * 100) + "% + 2px)";
        el.style.width = "calc(" + (100 / b.carriles) + "% - 4px)";
        el.style.right = "auto";
        el.style.top = ((minutos(b.inicio) - inicio) / 60 * alturaHora) + "px";
        el.style.height = Math.max((minutos(b.fin) - minutos(b.inicio)) / 60 * alturaHora - 2, 18) + "px";
        el.title = b.titulo + " · " + b.inicio + "–" + b.fin;
        var t = document.createElement("strong"); t.textContent = b.titulo;
        var s = document.createElement("span"); s.textContent = b.inicio + "–" + b.fin + (b.subtitulo ? " · " + b.subtitulo : "");
        el.appendChild(t); el.appendChild(s);
        col.appendChild(el);
      });
      contenedor.appendChild(col);
    }
  }

  // Asigna a cada bloque un carril (columna) dentro de su grupo de bloques superpuestos.
  function carriles(lista) {
    lista = lista.slice().sort(function (a, b) { return minutos(a.inicio) - minutos(b.inicio); });
    var grupo = [], finGrupo = -1, resultado = [];
    function cerrar() {
      var n = grupo.reduce(function (m, b) { return Math.max(m, b.carril + 1); }, 1);
      grupo.forEach(function (b) { b.carriles = n; resultado.push(b); });
      grupo = [];
    }
    lista.forEach(function (original) {
      var b = Object.assign({}, original);
      if (grupo.length && minutos(b.inicio) >= finGrupo) cerrar();
      var ocupados = grupo.filter(function (g) { return minutos(g.fin) > minutos(b.inicio); })
        .map(function (g) { return g.carril; });
      b.carril = 0;
      while (ocupados.indexOf(b.carril) !== -1) b.carril++;
      grupo.push(b);
      finGrupo = Math.max(finGrupo, minutos(b.fin));
    });
    if (grupo.length) cerrar();
    return resultado;
  }

  function celda(clase, texto) {
    var el = document.createElement("div");
    el.className = clase;
    el.textContent = texto;
    return el;
  }

  function bloquesDe(secciones, tipo) {
    var lista = [];
    secciones.forEach(function (s) {
      s.horarios.forEach(function (h) {
        lista.push({ dia: h.dia, inicio: h.inicio, fin: h.fin, titulo: s.asignatura, subtitulo: "P. " + s.paralelo, tipo: tipo, seccion: s.id });
      });
    });
    return lista;
  }

  window.CampusCalendario = { render: render, bloquesDe: bloquesDe, minutos: minutos };

  // Vista de solo lectura (Mis asignaturas, Versión B).
  var soloVigentes = document.querySelector("[data-calendario][data-solo-vigentes]");
  var datos = document.getElementById("datos-vigentes");
  if (soloVigentes && datos) {
    render(soloVigentes, bloquesDe(JSON.parse(datos.textContent), "vigente"));
  }
})();
