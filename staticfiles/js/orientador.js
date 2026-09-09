/**
 * Humm Financiamiento — Lógica de Interacción Accesible y Liviana
 * Vanilla JS sin dependencias externas
 */

document.addEventListener('DOMContentLoaded', () => {
  initOptionLabels();
  initCheckboxLimits();
  initModals();
  initVerMas();
  initSolicitudApoyo();
});

// 1. Resaltado visual de opciones seleccionadas
function initOptionLabels() {
  const inputs = document.querySelectorAll('.humm-option-input');
  
  function updateState(input) {
    if (input.type === 'radio') {
      const group = document.querySelectorAll(`input[name="${input.name}"]`);
      group.forEach(r => {
        const lbl = r.closest('.humm-option-label');
        if (lbl) lbl.classList.toggle('is-selected', r.checked);
      });
    } else {
      const lbl = input.closest('.humm-option-label');
      if (lbl) lbl.classList.toggle('is-selected', input.checked);
    }
  }

  inputs.forEach(input => {
    updateState(input);
    input.addEventListener('change', () => updateState(input));
  });
}

// 2. Control estricto de límite para necesidades (máximo 2) y opción exclusiva 'por_definir'
function initCheckboxLimits() {
  const containers = document.querySelectorAll('[data-limit-select]');
  containers.forEach(container => {
    const limit = parseInt(container.getAttribute('data-limit-select'), 10) || 2;
    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    const warningEl = container.querySelector('.humm-limit-warning');

    checkboxes.forEach(cb => {
      cb.addEventListener('change', (e) => {
        // Manejo de opción exclusiva 'por_definir' (Aún no tengo definida la inversión)
        if (cb.value === 'por_definir' && cb.checked) {
          checkboxes.forEach(other => {
            if (other !== cb && other.checked) {
              other.checked = false;
              const lbl = other.closest('.humm-option-label');
              if (lbl) lbl.classList.remove('is-selected');
            }
          });
        } else if (cb.checked && cb.value !== 'por_definir') {
          const porDefinirCb = container.querySelector('input[type="checkbox"][value="por_definir"]');
          if (porDefinirCb && porDefinirCb.checked) {
            porDefinirCb.checked = false;
            const lbl = porDefinirCb.closest('.humm-option-label');
            if (lbl) lbl.classList.remove('is-selected');
          }
        }

        const checkedCount = container.querySelectorAll('input[type="checkbox"]:checked').length;
        if (checkedCount > limit) {
          cb.checked = false;
          const lbl = cb.closest('.humm-option-label');
          if (lbl) lbl.classList.remove('is-selected');
          if (warningEl) {
            warningEl.style.display = 'block';
            warningEl.textContent = `Puedes elegir como máximo ${limit} necesidades principales.`;
            setTimeout(() => { warningEl.style.display = 'none'; }, 4000);
          }
        } else {
          if (warningEl) warningEl.style.display = 'none';
        }
      });
    });
  });
}

// 3. Modales nativos HTML5 (<dialog>) accesibles
function initModals() {
  const openButtons = document.querySelectorAll('[data-open-dialog]');
  openButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-open-dialog');
      const dialog = document.getElementById(targetId);
      if (dialog && typeof dialog.showModal === 'function') {
        dialog.showModal();
      }
    });
  });

  const closeButtons = document.querySelectorAll('[data-close-dialog]');
  closeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const dialog = btn.closest('dialog');
      if (dialog) dialog.close();
    });
  });

  // Cerrar al hacer clic en el backdrop
  document.querySelectorAll('dialog.humm-dialog').forEach(dialog => {
    dialog.addEventListener('click', (e) => {
      const rect = dialog.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX && e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        dialog.close();
      }
    });
  });
}

// 4. Botón "Ver más opciones"
function initVerMas() {
  const btnVerMas = document.getElementById('btn-ver-mas-opciones');
  const listaOculta = document.getElementById('lista-opciones-adicionales');
  if (btnVerMas && listaOculta) {
    btnVerMas.addEventListener('click', () => {
      const isHidden = listaOculta.style.display === 'none' || !listaOculta.style.display;
      listaOculta.style.display = isHidden ? 'block' : 'none';
      btnVerMas.textContent = isHidden ? 'Mostrar menos opciones' : 'Ver más opciones de financiamiento';
      if (isHidden) {
        listaOculta.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }
}

// 5. Manejo seguro de Solicitud de Apoyo (Protección anti-doble pulsación)
function initSolicitudApoyo() {
  const form = document.getElementById('form-solicitud-apoyo');
  if (!form) return;

  const btnSubmit = form.querySelector('button[type="submit"]');
  const feedbackEl = document.getElementById('solicitud-feedback');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.textContent = 'Enviando solicitud...';
    }

    const formData = new FormData(form);

    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      const data = await resp.json();
      if (data.ok) {
        if (feedbackEl) {
          feedbackEl.className = 'humm-alert-box estado-abierta';
          feedbackEl.innerHTML = `<strong>¡Solicitud recibida con éxito!</strong><br>${data.mensaje}`;
          feedbackEl.style.display = 'block';
        }
        form.reset();
        setTimeout(() => {
          const dialog = form.closest('dialog');
          if (dialog) dialog.close();
        }, 3500);
      } else {
        if (feedbackEl) {
          feedbackEl.className = 'humm-alert-box estado-cerrada';
          feedbackEl.innerHTML = `<strong>Hubo un problema:</strong> ${data.error || 'Revisa los campos.'}`;
          feedbackEl.style.display = 'block';
        }
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.textContent = 'Quiero apoyo para dar el siguiente paso';
        }
      }
    } catch (err) {
      if (feedbackEl) {
        feedbackEl.className = 'humm-alert-box estado-cerrada';
        feedbackEl.textContent = 'Error de conexión. Intenta nuevamente.';
        feedbackEl.style.display = 'block';
      }
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Quiero apoyo para dar el siguiente paso';
      }
    }
  });
}
