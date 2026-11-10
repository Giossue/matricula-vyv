/* Comportamiento general de la interfaz. */
(function () {
  "use strict";

  // Menú lateral en pantallas pequeñas.
  document.querySelectorAll("[data-menu-toggle]").forEach(function (el) {
    el.addEventListener("click", function () {
      document.body.classList.toggle("menu-abierto");
    });
  });

  // Confirmación antes de acciones sensibles (desactivar, retirar…).
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      if (!window.confirm(form.getAttribute("data-confirmar"))) ev.preventDefault();
    });
  });

  // Validación en el navegador antes de enviar formularios.
  document.querySelectorAll("form[data-validar]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      if (!form.checkValidity()) {
        ev.preventDefault();
        form.reportValidity();
      }
    });
  });

  // Indicador mientras corren las pruebas del laboratorio.
  document.querySelectorAll("form[data-ejecutar]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      var origen = ev.submitter;
      form.querySelectorAll("button").forEach(function (b) {
        if (b !== origen) b.disabled = true;
      });
      if (origen) {
        // Se conserva el valor del botón pulsado aunque se deshabilite.
        var oculto = document.createElement("input");
        oculto.type = "hidden"; oculto.name = origen.name; oculto.value = origen.value;
        form.appendChild(oculto);
        origen.textContent = "Ejecutando pruebas…";
        origen.disabled = true;
      }
    });
  });
})();
