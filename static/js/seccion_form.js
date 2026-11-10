/* Agrega filas de horario al formulario de sección (formset de Django). */
(function () {
  "use strict";
  var boton = document.querySelector("[data-agregar-horario]");
  var contenedor = document.querySelector("[data-horarios]");
  var plantilla = document.querySelector("[data-plantilla-horario]");
  var total = document.getElementById("id_horarios-TOTAL_FORMS");
  var maximo = document.getElementById("id_horarios-MAX_NUM_FORMS");
  if (!boton || !contenedor || !plantilla || !total) return;
  boton.addEventListener("click", function () {
    var indice = parseInt(total.value, 10);
    if (maximo && indice >= parseInt(maximo.value, 10)) {
      window.alert("Una sección admite como máximo " + maximo.value + " bloques de horario.");
      return;
    }
    var html = plantilla.innerHTML.replace(/__prefix__/g, String(indice));
    contenedor.insertAdjacentHTML("beforeend", html);
    total.value = String(indice + 1);
  });
})();
