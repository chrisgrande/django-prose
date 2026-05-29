;(function () {
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
  }

  function formatSize(bytes) {
    var n = Number(bytes) || 0
    if (n < 1024) return n + " B"
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"
    return (n / (1024 * 1024)).toFixed(1) + " MB"
  }

  function attachmentHtml(payload) {
    var ct = escapeHtml(payload.content_type || "")
    var filename = escapeHtml(payload.filename || "file")
    if (payload.kind === "image") {
      return (
        '<figure class="django-prose-attachment django-prose-attachment--image" data-content-type="' +
        ct +
        '"><img src="' +
        escapeHtml(payload.url) +
        '" alt="' +
        filename +
        '"><figcaption></figcaption></figure>'
      )
    }
    var href = escapeHtml(payload.download_url || payload.url)
    return (
      '<figure class="django-prose-attachment django-prose-attachment--file" data-content-type="' +
      ct +
      '"><a href="' +
      href +
      '">' +
      filename +
      '</a><figcaption>' +
      escapeHtml(formatSize(payload.size || 0)) +
      "</figcaption></figure>"
    )
  }

  function insertAttachmentHtml(editorElement, html) {
    // Lexxy's insertHtml uses Contents.insertDOM, which no-ops unless there is a
    // *range* selection. Toolbar uploads move focus to the button, so we must
    // focus the editor, restore the caret, then insert on the next frame.
    function appendViaValue() {
      var current = editorElement.value || ""
      editorElement.value = current + html
    }

    if (!editorElement.contents || typeof editorElement.contents.insertHtml !== "function") {
      appendViaValue()
      return
    }

    if (typeof editorElement.focus === "function") {
      editorElement.focus()
    }
    if (editorElement.selection && typeof editorElement.selection.placeCursorAtTheEnd === "function") {
      editorElement.selection.placeCursorAtTheEnd()
    }

    var before = editorElement.value || ""

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        try {
          if (typeof editorElement.focus === "function") {
            editorElement.focus()
          }
          if (editorElement.selection && typeof editorElement.selection.placeCursorAtTheEnd === "function") {
            editorElement.selection.placeCursorAtTheEnd()
          }
          editorElement.contents.insertHtml(html)
        } catch (e) {
          appendViaValue()
          return
        }

        // insertHtml can still no-op without throwing if selection was not a range.
        setTimeout(function () {
          var after = editorElement.value || ""
          if (after === before) {
            appendViaValue()
          }
        }, 50)
      })
    })
  }

  function getCookie(name) {
    var value = "; " + document.cookie
    var parts = value.split("; " + name + "=")
    if (parts.length === 2) {
      return parts.pop().split(";").shift()
    }
    return ""
  }

  /**
   * Django CSRF: hidden input, optional meta tag, or csrftoken cookie.
   * Do not append a fake "Content-Type" form field — it can break multipart parsing
   * and yield 400 / MultiPartParserError before the view runs.
   */
  function getCsrfToken() {
    var input = document.querySelector("input[name=csrfmiddlewaretoken]")
    if (input && input.value) {
      return input.value
    }
    var meta = document.querySelector('meta[name="csrf-token"]')
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content")
    }
    return getCookie("csrftoken") || ""
  }

  function uploadFile(host, file, progressCallback, successCallback, errorCallback) {
    var formData = new FormData()
    var xhr = new XMLHttpRequest()

    formData.append("file", file)

    var csrfToken = getCsrfToken()
    if (csrfToken) {
      formData.append("csrfmiddlewaretoken", csrfToken)
    }

    xhr.open("POST", host, true)
    if (csrfToken) {
      xhr.setRequestHeader("X-CSRFToken", csrfToken)
    }

    xhr.upload.addEventListener("progress", function (event) {
      if (event.lengthComputable && typeof progressCallback === "function") {
        var progress = (event.loaded / event.total) * 100
        progressCallback(progress)
      }
    })

    xhr.addEventListener("load", function () {
      if (xhr.status === 201) {
        try {
          var data = JSON.parse(xhr.responseText)
          if (data && data.url && data.kind) {
            successCallback(data)
          } else if (typeof errorCallback === "function") {
            errorCallback(new Error("Invalid upload response"))
          }
        } catch (e) {
          if (typeof errorCallback === "function") {
            errorCallback(e)
          }
        }
      } else {
        var message = "Upload failed with status " + xhr.status
        try {
          var err = JSON.parse(xhr.responseText)
          if (err && err.error) message = err.error
        } catch (e2) {}
        if (typeof errorCallback === "function") {
          errorCallback(new Error(message))
        }
      }
    })

    xhr.addEventListener("error", function () {
      if (typeof errorCallback === "function") {
        errorCallback(new Error("Network error during upload"))
      }
    })

    xhr.send(formData)
  }

  function queueUploads(host, editorElement, files) {
    if (!files || !files.length) return
    var list = Array.prototype.slice.call(files)
    list.forEach(function (file) {
      uploadFile(
        host,
        file,
        function () {},
        function (payload) {
          insertAttachmentHtml(editorElement, attachmentHtml(payload))
        },
        function () {}
      )
    })
  }

  function bindPasteAndDrop(host, editorElement) {
    editorElement.addEventListener(
      "paste",
      function (e) {
        var files = e.clipboardData && e.clipboardData.files
        if (!files || !files.length) return
        e.preventDefault()
        queueUploads(host, editorElement, files)
      },
      true
    )

    editorElement.addEventListener("dragover", function (e) {
      e.preventDefault()
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"
    })

    editorElement.addEventListener("drop", function (e) {
      var files = e.dataTransfer && e.dataTransfer.files
      if (!files || !files.length) return
      e.preventDefault()
      queueUploads(host, editorElement, files)
    })
  }

  /**
   * Use Lexxy's default "Upload files" toolbar button (name="file") with Lexxy styling,
   * but route uploads to Django instead of ActiveStorage.
   */
  function wireDefaultFileUploadButton(lexxyToolbar, editorElement, host, attempt) {
    attempt = attempt || 0
    var fileBtn = lexxyToolbar.querySelector('button[name="file"]')
    if (!fileBtn) {
      if (attempt < 20) {
        requestAnimationFrame(function () {
          wireDefaultFileUploadButton(lexxyToolbar, editorElement, host, attempt + 1)
        })
      }
      return
    }
    if (fileBtn.dataset.djangoProseWired === "1") return
    fileBtn.dataset.djangoProseWired = "1"

    var fileInput = document.createElement("input")
    fileInput.type = "file"
    fileInput.multiple = true
    fileInput.accept = "*/*"
    fileInput.style.display = "none"

    fileBtn.addEventListener(
      "click",
      function (e) {
        e.preventDefault()
        e.stopPropagation()
        e.stopImmediatePropagation()
        fileInput.click()
      },
      true
    )

    fileInput.addEventListener("change", function () {
      if (!fileInput.files || !fileInput.files.length) return
      queueUploads(host, editorElement, fileInput.files)
      fileInput.value = ""
    })

    lexxyToolbar.appendChild(fileInput)
  }

  // Dynamically import Lexxy from esm.sh so we don't depend on a bundler
  import("https://esm.sh/@37signals/lexxy@0.9.0-beta")
    .then(function (Lexxy) {
      if (!Lexxy || typeof Lexxy.configure !== "function" || !Lexxy.Extension) return

      function uploadUrlFromEditor(el) {
        return (
          el.dataset.uploadAttachmentUrl ||
          el.getAttribute("data-upload-attachment-url") ||
          ""
        )
      }

      class DjangoProseUploadExtension extends Lexxy.Extension {
        get enabled() {
          return !!uploadUrlFromEditor(this.editorElement)
        }

        initializeToolbar(lexxyToolbar) {
          var host = uploadUrlFromEditor(this.editorElement)
          if (!host) return

          var editorElement = this.editorElement

          if (!editorElement.dataset.djangoProseAttachmentsBound) {
            editorElement.dataset.djangoProseAttachmentsBound = "1"
            bindPasteAndDrop(host, editorElement)
          }

          wireDefaultFileUploadButton(lexxyToolbar, editorElement, host)
        }
      }

      Lexxy.configure({
        global: {
          // Ensure Lexxy never emits <action-text-attachment> tags,
          // which Django Prose does not recognize or allow.
          attachmentTagName: "img",
          extensions: [DjangoProseUploadExtension],
        },
        default: {
          // Disable Lexxy's built-in ActiveStorage-based attachments;
          // we provide our own Django-specific upload behavior instead.
          attachments: false,
          // Single default upload control: Lexxy's "file" button (not image + file).
          toolbar: {
            upload: "file",
          },
        },
      })
    })
    .catch(function () {
      // Silently ignore failures; the page should still work as a normal form.
    })
})()
