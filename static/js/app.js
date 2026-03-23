document.addEventListener('DOMContentLoaded', () => {
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
    const clearButton = container.querySelector('[data-searchable-multiselect-clear]');
    const selectVisibleButton = container.querySelector('[data-searchable-multiselect-select-visible]');
    const optionsList = Array.from(container.querySelectorAll('[data-searchable-multiselect-option]'));
    const selectedContainer = container.querySelector('[data-searchable-multiselect-selected]');

    if (!select || !input || !summary || !empty || !selectedContainer) return;

    const options = Array.from(select.options);
    const byValue = new Map(options.map((option) => [String(option.value), option]));
    const optionButtons = new Map(optionsList.map((button) => [button.dataset.value, button]));

    const updateSummary = () => {
      const selected = options.filter((option) => option.selected);
      if (selected.length === 0) {
        summary.textContent = 'Cap element seleccionat';
      } else if (selected.length === 1) {
        summary.textContent = `1 element seleccionat`;
      } else {
        summary.textContent = `${selected.length} elements seleccionats`;
      }
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
          select.dispatchEvent(new Event('change', { bubbles: true }));
        });
        selectedContainer.appendChild(tag);
      });

      selectedContainer.classList.remove('d-none');
    };

    const syncButtonState = (value) => {
      const button = optionButtons.get(String(value));
      const option = byValue.get(String(value));
      if (!button || !option) return;
      button.classList.toggle('is-selected', option.selected);
      button.setAttribute('aria-pressed', option.selected ? 'true' : 'false');
    };

    const syncAllButtons = () => {
      options.forEach((option) => syncButtonState(String(option.value)));
      updateSummary();
      renderSelected();
    };

    const filterOptions = () => {
      const query = input.value.trim().toLowerCase();
      let visibleCount = 0;

      options.forEach((option) => {
        const matches = option.text.toLowerCase().includes(query);
        option.hidden = !matches;
        const button = optionButtons.get(String(option.value));
        if (button) {
          button.classList.toggle('d-none', !matches);
        }
        if (matches) visibleCount += 1;
      });

      empty.classList.toggle('d-none', visibleCount > 0);
    };

    input.addEventListener('input', filterOptions);
    select.addEventListener('change', syncAllButtons);

    optionsList.forEach((button) => {
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
        options.forEach((option) => { option.selected = false; });
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
});
