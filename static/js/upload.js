/**
 * Resume upload page: drag-and-drop file collection + XHR upload with a
 * real progress bar (a plain form POST can't report upload progress).
 */
(function () {
  const form = document.getElementById('resumeUploadForm');
  if (!form) return;

  const dropzone = document.getElementById('dropzone');
  const input = document.getElementById('resumeFiles');
  const fileListEl = document.getElementById('fileList');
  const submitBtn = document.getElementById('uploadSubmitBtn');
  const progressWrap = document.getElementById('uploadProgressWrap');
  const progressBar = document.getElementById('uploadProgressBar');
  const progressLabel = document.getElementById('uploadProgressLabel');
  const redirectUrl = form.dataset.redirectUrl;

  let currentFiles = [];

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function renderFileList() {
    fileListEl.innerHTML = '';
    currentFiles.forEach(function (file, index) {
      const li = document.createElement('li');
      li.className = 'ars-file-item';

      const label = document.createElement('span');
      label.textContent = file.name + ' (' + formatSize(file.size) + ')';

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'ars-file-remove';
      removeBtn.setAttribute('aria-label', 'Remove ' + file.name);
      removeBtn.textContent = '\u00D7';
      removeBtn.addEventListener('click', function () {
        currentFiles.splice(index, 1);
        renderFileList();
      });

      li.appendChild(label);
      li.appendChild(removeBtn);
      fileListEl.appendChild(li);
    });
    submitBtn.disabled = currentFiles.length === 0;
  }

  function addFiles(fileListLike) {
    Array.from(fileListLike).forEach(function (file) {
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      const alreadyAdded = currentFiles.some(function (f) {
        return f.name === file.name && f.size === file.size;
      });
      if (isPdf && !alreadyAdded) {
        currentFiles.push(file);
      }
    });
    renderFileList();
  }

  dropzone.addEventListener('click', function () {
    input.click();
  });
  dropzone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      input.click();
    }
  });
  input.addEventListener('change', function () {
    addFiles(input.files);
  });

  ['dragenter', 'dragover'].forEach(function (evtName) {
    dropzone.addEventListener(evtName, function (e) {
      e.preventDefault();
      dropzone.classList.add('ars-dropzone-active');
    });
  });
  ['dragleave', 'drop'].forEach(function (evtName) {
    dropzone.addEventListener(evtName, function (e) {
      e.preventDefault();
      dropzone.classList.remove('ars-dropzone-active');
    });
  });
  dropzone.addEventListener('drop', function (e) {
    if (e.dataTransfer && e.dataTransfer.files) {
      addFiles(e.dataTransfer.files);
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (currentFiles.length === 0) return;

    const formData = new FormData();
    currentFiles.forEach(function (file) {
      formData.append('resume_files', file);
    });

    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action, true);

    xhr.upload.addEventListener('progress', function (evt) {
      if (evt.lengthComputable) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        progressWrap.classList.remove('d-none');
        progressBar.style.width = pct + '%';
        progressLabel.textContent = 'Uploading… ' + pct + '%';
      }
    });

    xhr.onload = function () {
      window.location.href = redirectUrl;
    };
    xhr.onerror = function () {
      progressLabel.textContent = 'Upload failed. Please try again.';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Upload';
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading…';
    xhr.send(formData);
  });
})();
