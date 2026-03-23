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

    if (!select || !input || !summary || !empty) return;

    const options = Array.from(select.options);

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

    const filterOptions = () => {
      const query = input.value.trim().toLowerCase();
      let visibleCount = 0;

      options.forEach((option) => {
        const matches = option.text.toLowerCase().includes(query);
        option.hidden = !matches;
        if (matches) visibleCount += 1;
      });

      empty.classList.toggle('d-none', visibleCount > 0);
    };

    input.addEventListener('input', filterOptions);
    select.addEventListener('change', updateSummary);

    if (clearButton) {
      clearButton.addEventListener('click', () => {
        input.value = '';
        filterOptions();
        input.focus();
      });
    }

    updateSummary();
    filterOptions();
  });
});
