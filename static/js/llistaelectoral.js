(() => {
  const pageRoot = document.querySelector('[data-llista-electoral]');
  if (!pageRoot) {
    return;
  }

  const csrfToken =
    document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
    (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];
  let dragData = null;

  const postJson = async (url, payload) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload || {}),
    });

    if (!response.ok) {
      throw new Error('Request failed');
    }

    return response;
  };

  const collectElectoralText = () => {
    const rows = Array.from(document.querySelectorAll('tr.drop-zone'))
      .map((row) => {
        const position = row.dataset.position;
        const name = row.querySelector('[data-integrant-name]')?.textContent?.trim() || '';
        const affiliation =
          row.querySelector('[data-field="afiliacio"]')?.selectedOptions?.[0]?.textContent || '—';
        const status =
          row.querySelector('[data-field="estat"]')?.selectedOptions?.[0]?.textContent || '—';
        const notes = row.querySelector('[data-field="observacions"]')?.value?.trim() || '';

        if (!name) {
          return null;
        }

        return `#${position} ${name} · ${affiliation} · ${status}${
          notes ? ` · Obs: ${notes}` : ''
        }`;
      })
      .filter(Boolean);

    return `Llista electoral\n\n${rows.join('\n')}`;
  };

  document.querySelector('[data-copy-electoral]')?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(collectElectoralText());
      window.alert('Llista copiada al porta-retalls.');
    } catch (error) {
      window.alert('No s’ha pogut copiar el text.');
    }
  });

  document.querySelector('[data-share-whatsapp]')?.addEventListener('click', () => {
    const text = encodeURIComponent(collectElectoralText());
    window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener');
  });

  document.querySelectorAll('[data-filter-select]').forEach((input) => {
    const select = document.getElementById(input.dataset.filterSelect);
    if (!select) {
      return;
    }

    const options = Array.from(select.options);
    input.addEventListener('input', () => {
      const query = input.value.trim().toLowerCase();
      options.forEach((option) => {
        if (!option.value) {
          return;
        }
        option.hidden = query.length > 0 && !option.text.toLowerCase().includes(query);
      });

      if (query.length > 0) {
        const firstMatch = options.find((option) => option.value && !option.hidden);
        if (firstMatch) {
          select.value = firstMatch.value;
        }
      }
    });
  });

  document.querySelectorAll('.draggable-integrant').forEach((element) => {
    element.addEventListener('dragstart', () => {
      dragData = {
        integrantId: element.dataset.integrant,
        sourcePosition: element.dataset.sourcePosition || null,
      };
    });
  });

  document.querySelectorAll('.drop-zone').forEach((zone) => {
    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
      zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', async () => {
      zone.classList.remove('drag-over');
      if (!dragData) {
        return;
      }

      await postJson(pageRoot.dataset.assignUrl, {
        integrant_id: dragData.integrantId,
        source_position: dragData.sourcePosition,
        target_position: zone.dataset.position,
      });
      window.location.reload();
    });
  });

  document.querySelectorAll('.inline-edit[data-field="observacions"]').forEach((input) => {
    input.addEventListener('blur', async () => {
      await postJson(input.dataset.editUrl, {
        observacions: input.value,
      });
    });
  });

  document.querySelectorAll('.inline-edit:not([data-field="observacions"])').forEach((select) => {
    select.addEventListener('change', async () => {
      await postJson(select.dataset.editUrl, {
        [select.dataset.field]: select.value,
      });
    });
  });

  document.querySelectorAll('[data-remove-position]').forEach((button) => {
    button.addEventListener('click', async () => {
      await postJson(pageRoot.dataset.removePositionUrl, {
        position: button.dataset.position,
      });
      window.location.reload();
    });
  });

  document.querySelectorAll('[data-delete-integrant]').forEach((button) => {
    button.addEventListener('click', async () => {
      await postJson(pageRoot.dataset.deleteIntegrantUrl, {
        integrant_id: button.dataset.integrant,
      });
      window.location.reload();
    });
  });

  const form = document.getElementById('add-integrant-form');
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      await postJson(pageRoot.dataset.createUrl, payload);
      window.location.reload();
    } catch (error) {
      window.alert('No s\'ha pogut crear l\'integrant.');
    }
  });
})();
