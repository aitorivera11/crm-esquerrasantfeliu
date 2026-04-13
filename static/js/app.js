document.addEventListener('DOMContentLoaded', () => {

  document.querySelectorAll('.filters-panel').forEach((details) => {
    const label = details.querySelector('.filter-toggle-label');
    const dayInput = details.querySelector('#filter-day');
    const fromInput = details.querySelector('#filter-date-from');
    const toInput = details.querySelector('#filter-date-to');

    const syncToggleLabel = () => {
      if (!label) return;
      label.textContent = details.open ? (label.dataset.expandedLabel || 'Ocultar filtres') : (label.dataset.collapsedLabel || 'Mostrar filtres');
    };

    syncToggleLabel();
    details.addEventListener('toggle', syncToggleLabel);

    if (dayInput && fromInput && toInput) {
      dayInput.addEventListener('change', () => {
        if (dayInput.value) {
          fromInput.value = dayInput.value;
          toInput.value = dayInput.value;
        }
      });

      const clearSingleDay = () => {
        if (dayInput.value && (fromInput.value !== dayInput.value || toInput.value !== dayInput.value)) {
          dayInput.value = '';
        }
      };

      fromInput.addEventListener('change', clearSingleDay);
      toInput.addEventListener('change', clearSingleDay);
    }
  });
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('[data-searchable-multiselect]').forEach((container) => {
    const select = container.querySelector('[data-searchable-multiselect-select]');
    const input = container.querySelector('[data-searchable-multiselect-input]');
    const summary = container.querySelector('[data-searchable-multiselect-summary]');
    const empty = container.querySelector('[data-searchable-multiselect-empty]');
    const hint = container.querySelector('[data-searchable-multiselect-hint]');
    const clearButton = container.querySelector('[data-searchable-multiselect-clear]');
    const selectVisibleButton = container.querySelector('[data-searchable-multiselect-select-visible]');
    const optionsContainer = container.querySelector('[data-searchable-multiselect-options]');
    const optionButtons = Array.from(container.querySelectorAll('[data-searchable-multiselect-option]'));
    const selectedContainer = container.querySelector('[data-searchable-multiselect-selected]');
    const minQueryLength = 1;

    if (!select || !input || !summary || !empty || !selectedContainer || !optionsContainer) return;

    const options = Array.from(select.options);
    const byValue = new Map(options.map((option) => [String(option.value), option]));
    const buttonByValue = new Map(optionButtons.map((button) => [button.dataset.value, button]));

    const updateSummary = () => {
      const selected = options.filter((option) => option.selected);
      if (selected.length === 0) {
        summary.textContent = 'Cap element seleccionat';
      } else if (selected.length === 1) {
        summary.textContent = '1 element seleccionat';
      } else {
        summary.textContent = `${selected.length} elements seleccionats`;
      }
    };

    const syncButtonState = (value) => {
      const button = buttonByValue.get(String(value));
      const option = byValue.get(String(value));
      if (!button || !option) return;
      button.classList.toggle('is-selected', option.selected);
      button.setAttribute('aria-pressed', option.selected ? 'true' : 'false');
    };

    const renderSelected = () => {
      const selected = options.filter((option) => option.selected);
      selectedContainer.innerHTML = '';

      if (selected.length === 0) {
        selectedContainer.classList.add('d-none');
        return;
      }

      selected.forEach((option) => {
        const tag = document.createElement('span');
        tag.className = 'searchable-multiselect__tag';
        tag.innerHTML = `<span>${option.text}</span><button type="button" aria-label="Treure ${option.text}">×</button>`;
        tag.querySelector('button').addEventListener('click', () => {
          option.selected = false;
          syncButtonState(String(option.value));
          filterOptions();
          select.dispatchEvent(new Event('change', { bubbles: true }));
        });
        selectedContainer.appendChild(tag);
      });

      selectedContainer.classList.remove('d-none');
    };

    const updateActionState = (hasVisibleOptions) => {
      if (selectVisibleButton) {
        selectVisibleButton.disabled = !hasVisibleOptions;
      }
    };

    const filterOptions = () => {
      const query = input.value.trim().toLowerCase();
      const hasQuery = query.length >= minQueryLength;
      let visibleCount = 0;

      options.forEach((option) => {
        const matches = hasQuery && option.text.toLowerCase().includes(query);
        option.hidden = !matches;
        const button = buttonByValue.get(String(option.value));
        if (button) {
          button.classList.toggle('d-none', !matches);
        }
        if (matches) visibleCount += 1;
      });

      optionsContainer.classList.toggle('d-none', !hasQuery || visibleCount === 0);
      empty.classList.toggle('d-none', !hasQuery || visibleCount > 0);
      if (hint) {
        hint.classList.toggle('d-none', hasQuery);
      }
      updateActionState(hasQuery && visibleCount > 0);
    };

    const syncAllButtons = () => {
      options.forEach((option) => syncButtonState(String(option.value)));
      updateSummary();
      renderSelected();
    };

    input.addEventListener('input', filterOptions);
    select.addEventListener('change', syncAllButtons);

    optionButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const option = byValue.get(button.dataset.value);
        if (!option) return;
        option.selected = !option.selected;
        syncButtonState(button.dataset.value);
        select.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });

    if (clearButton) {
      clearButton.addEventListener('click', () => {
        input.value = '';
        options.forEach((option) => {
          option.selected = false;
        });
        filterOptions();
        select.dispatchEvent(new Event('change', { bubbles: true }));
        input.focus();
      });
    }

    if (selectVisibleButton) {
      selectVisibleButton.addEventListener('click', () => {
        options.forEach((option) => {
          if (!option.hidden) option.selected = true;
        });
        select.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    syncAllButtons();
    filterOptions();
  });

  document.querySelectorAll('[data-copy-text]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = button.dataset.copyText || '';
      const original = button.querySelector('strong')?.textContent || button.textContent;
      const feedback = button.dataset.copyFeedback || 'Copiat';

      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          const helper = document.createElement('textarea');
          helper.value = text;
          helper.setAttribute('readonly', 'readonly');
          helper.style.position = 'absolute';
          helper.style.left = '-9999px';
          document.body.appendChild(helper);
          helper.select();
          document.execCommand('copy');
          document.body.removeChild(helper);
        }

        const label = button.querySelector('strong');
        if (label) {
          label.textContent = feedback;
          window.setTimeout(() => {
            label.textContent = original;
          }, 1800);
        }
      } catch (error) {
        window.alert('No s’ha pogut copiar l’enllaç.');
      }
    });
  });

  document.querySelectorAll('[data-native-share]').forEach((button) => {
    if (!navigator.share) {
      button.classList.add('d-none');
      return;
    }

    button.addEventListener('click', async () => {
      try {
        await navigator.share({
          title: button.dataset.shareTitle,
          text: button.dataset.shareText,
          url: button.dataset.shareUrl,
        });
      } catch (error) {
        if (error?.name !== 'AbortError') {
          window.alert('No s’ha pogut obrir el menú de compartir.');
        }
      }
    });
  });

  document.querySelectorAll('[data-file-dropzone]').forEach((dropzone) => {
    const input = dropzone.querySelector('input[type="file"]');
    const fileName = dropzone.querySelector('[data-file-dropzone-name]');
    if (!input) return;

    const updateFileName = () => {
      if (!fileName) return;
      const selected = input.files?.[0];
      fileName.textContent = selected ? selected.name : 'Cap fitxer seleccionat.';
    };

    ['dragenter', 'dragover'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'dragend', 'drop'].forEach((eventName) => {
      dropzone.addEventListener(eventName, () => {
        dropzone.classList.remove('is-dragover');
      });
    });

    dropzone.addEventListener('drop', (event) => {
      event.preventDefault();
      const files = event.dataTransfer?.files;
      if (!files || files.length === 0) return;
      input.files = files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    input.addEventListener('change', updateFileName);
    updateFileName();
  });

  const getCsrfToken = () => {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const autosaveStatus = document.querySelector('[data-autosave-status]');
  const setAutosaveStatus = (text, isError = false) => {
    if (!autosaveStatus) return;
    autosaveStatus.textContent = text;
    autosaveStatus.classList.toggle('text-danger', isError);
  };

  const saveTimers = new WeakMap();
  document.querySelectorAll('[data-quick-save]').forEach((field) => {
    const feedbackNode = field.closest('[data-acta-point]')?.querySelector('[data-point-feedback]');

    const runSave = async () => {
      setAutosaveStatus('Desant...');
      try {
        const formData = new URLSearchParams({
          field: field.dataset.field || '',
          value: field.value || '',
        });
        const response = await fetch(field.dataset.url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'X-CSRFToken': getCsrfToken(),
          },
          body: formData.toString(),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || 'No s’ha pogut desar');
        }
        setAutosaveStatus(`Desat a les ${payload.updated}`);
        if (feedbackNode) feedbackNode.textContent = payload.updated;
      } catch (error) {
        setAutosaveStatus('Error en desar', true);
      }
    };

    field.addEventListener('input', () => {
      const currentTimer = saveTimers.get(field);
      if (currentTimer) window.clearTimeout(currentTimer);
      setAutosaveStatus('Pendent de desar...');
      const timer = window.setTimeout(runSave, 700);
      saveTimers.set(field, timer);
    });

    field.addEventListener('blur', () => {
      const currentTimer = saveTimers.get(field);
      if (currentTimer) {
        window.clearTimeout(currentTimer);
      }
      runSave();
    });
  });

  const renderTaskChip = (task) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'd-flex gap-2 align-items-center';
    wrapper.dataset.taskChip = '';
    wrapper.dataset.taskId = task.id;

    const link = document.createElement('a');
    link.href = task.url;
    link.className = 'task-chip-link flex-grow-1';
    link.innerHTML = `<strong>${task.title}</strong><span class="small text-muted">${task.status} · ${task.responsable}</span>`;
    wrapper.appendChild(link);

    if (task.can_delete && task.delete_url) {
      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.className = 'btn btn-sm btn-outline-danger';
      deleteButton.textContent = 'Eliminar';
      deleteButton.dataset.taskDeleteUrl = task.delete_url;
      deleteButton.dataset.taskDelete = '';
      wrapper.appendChild(deleteButton);
    }

    return wrapper;
  };

  document.querySelectorAll('[data-point-quick-task-form]').forEach((form) => {
    const feedback = form.querySelector('[data-point-quick-task-feedback]');
    const taskListSelector = form.dataset.taskList;
    const taskList = taskListSelector ? document.querySelector(taskListSelector) : null;

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (feedback) feedback.textContent = 'Creant tasca...';
      try {
        const response = await fetch(form.dataset.url, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: new FormData(form),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || 'No s’ha pogut crear la tasca');
        }
        if (taskList) {
          taskList.querySelector('[data-empty-point-tasks]')?.remove();
          taskList.prepend(renderTaskChip(payload.task));
        }
        form.reset();
        if (feedback) feedback.textContent = `Tasca creada: ${payload.task.title}`;
      } catch (error) {
        if (feedback) feedback.textContent = error.message || 'Error en crear la tasca.';
      }
    });
  });

  const collectCommands = (pointNode) => {
    const fields = pointNode.querySelectorAll('[data-command-url]');
    const commands = [];
    let commandUrl = '';
    fields.forEach((field) => {
      commandUrl = commandUrl || field.dataset.commandUrl;
      field.value.split('\n').forEach((line) => {
        if (line.trim().toLowerCase().startsWith('@tasca')) {
          commands.push(line.trim());
        }
      });
    });
    return { commands, commandUrl };
  };

  document.querySelectorAll('[data-create-task-from-command]').forEach((button) => {
    button.addEventListener('click', async () => {
      const pointNode = button.closest('[data-acta-point]');
      const feedback = pointNode?.querySelector('[data-command-feedback]');
      if (!pointNode) return;
      const { commands, commandUrl } = collectCommands(pointNode);
      if (!commands.length || !commandUrl) {
        if (feedback) feedback.textContent = 'No s’han trobat comandes @tasca en aquest punt.';
        return;
      }
      if (feedback) feedback.textContent = 'Creant tasques des de comandes...';
      try {
        const formData = new URLSearchParams({ content: commands.join('\n') });
        const response = await fetch(commandUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'X-CSRFToken': getCsrfToken(),
          },
          body: formData.toString(),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || 'No s’han pogut processar les comandes.');
        }
        const targetSelector = button.dataset.targetPointList;
        const taskList = targetSelector ? document.querySelector(targetSelector) : null;
        if (taskList) {
          taskList.querySelector('[data-empty-point-tasks]')?.remove();
          (payload.tasks || []).forEach((task) => taskList.prepend(renderTaskChip(task)));
        }
        const createdCount = (payload.tasks || []).length;
        const skippedCount = (payload.skipped || []).length;
        const errorsCount = (payload.errors || []).length;
        if (feedback) {
          feedback.textContent = `Creades ${createdCount} tasques${skippedCount ? ` · ${skippedCount} ja existien` : ''}${errorsCount ? ` · ${errorsCount} comandes amb errors` : ''}.`;
        }
      } catch (error) {
        if (feedback) feedback.textContent = error.message || 'Error en processar comandes.';
      }
    });
  });

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-task-delete]');
    if (!button) return;
    const deleteUrl = button.dataset.taskDeleteUrl;
    if (!deleteUrl) return;
    event.preventDefault();

    try {
      const response = await fetch(deleteUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'No s’ha pogut eliminar la tasca.');
      }
      const taskChip = button.closest('[data-task-chip]');
      const taskList = taskChip?.parentElement;
      taskChip?.remove();
      if (taskList && !taskList.querySelector('[data-task-chip]')) {
        const empty = document.createElement('div');
        empty.className = 'small text-muted';
        empty.dataset.emptyPointTasks = '';
        empty.textContent = 'Encara no hi ha tasques vinculades.';
        taskList.appendChild(empty);
      }
    } catch (error) {
      const pointNode = button.closest('[data-acta-point]');
      const feedback = pointNode?.querySelector('[data-command-feedback]');
      if (feedback) feedback.textContent = error.message || 'Error en eliminar la tasca.';
    }
  });
});
