(function () {
  async function fetchCatalogData(upc, feedback, options = {}) {
    const lookupUrl = options.lookupUrl;
    if (!lookupUrl || !upc) return;

    try {
      const response = await fetch(`${lookupUrl}?upc=${encodeURIComponent(upc)}`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        if (feedback) feedback.textContent = payload.error || 'Sense dades addicionals per aquest codi.';
        return;
      }

      if (options.descriptionSelector) {
        const descriptionInput = document.querySelector(options.descriptionSelector);
        if (descriptionInput && !descriptionInput.value.trim()) {
          descriptionInput.value = payload.item.title || payload.item.description || '';
          descriptionInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
      if (feedback) {
        feedback.textContent = payload.item.title
          ? `Producte detectat: ${payload.item.title}`
          : 'Producte trobat a UPCitemdb.';
      }
    } catch (err) {
      if (feedback) feedback.textContent = 'No s’ha pogut consultar UPCitemdb.';
    }
  }

  async function startScan(inputSelector, feedbackSelector, options = {}) {
    const input = document.querySelector(inputSelector);
    const feedback = document.querySelector(feedbackSelector);
    const video = document.getElementById(options.videoElementId || 'material-scan-video');
    if (!input) return;

    const setFeedback = (msg, isError) => {
      if (!feedback) return;
      feedback.textContent = msg;
      feedback.classList.toggle('text-danger', !!isError);
      feedback.classList.toggle('text-muted', !isError);
    };

    const showVideoPreview = () => {
      if (!video) return;
      video.classList.remove('d-none');
      video.classList.add('scanner-preview');
    };

    const hideVideoPreview = () => {
      if (!video) return;
      video.pause();
      video.srcObject = null;
      video.classList.add('d-none');
      video.classList.remove('scanner-preview');
    };

    const handleCode = async (code) => {
      if (!code) return;
      input.value = code;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      setFeedback('Codi detectat correctament.', false);
      await fetchCatalogData(code, feedback, options);
      hideVideoPreview();
    };

    if ('BarcodeDetector' in window) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        if (!video) throw new Error('No hi ha element de vídeo disponible');
        showVideoPreview();
        video.srcObject = stream;
        video.setAttribute('playsinline', 'true');
        video.muted = true;
        await video.play();
        const detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'] });
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        setFeedback('Escanejant amb càmera...', false);

        const scanInterval = setInterval(async () => {
          if (video.readyState < 2) return;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const barcodes = await detector.detect(canvas);
          if (barcodes.length) {
            const code = barcodes[0]?.rawValue;
            clearInterval(scanInterval);
            stream.getTracks().forEach((track) => track.stop());
            await handleCode(code);
          }
        }, 400);
        return;
      } catch (err) {
        hideVideoPreview();
        setFeedback('No s’ha pogut utilitzar BarcodeDetector. S’activa el fallback.', true);
      }
    }

    if (window.ZXing && window.ZXing.BrowserMultiFormatReader) {
      const reader = new window.ZXing.BrowserMultiFormatReader();
      setFeedback('Escanejant amb fallback ZXing...', false);
      try {
        showVideoPreview();
        const result = await reader.decodeOnceFromVideoDevice(undefined, options.videoElementId || 'material-scan-video');
        await handleCode(result.text);
      } catch (err) {
        hideVideoPreview();
        setFeedback('No s’ha pogut detectar cap codi. Introdueix-lo manualment.', true);
      } finally {
        reader.reset();
        hideVideoPreview();
      }
    } else {
      setFeedback('Navegador sense suport d’escàner. Introdueix el codi manualment.', true);
    }
  }

  window.MaterialBarcodeScanner = { startScan };
})();
