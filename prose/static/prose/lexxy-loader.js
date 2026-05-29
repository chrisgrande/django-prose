;(function () {
  var LEXXY_MODULE = "https://esm.sh/@37signals/lexxy@0.9.14-beta"
  var YOUTUBE_CONTENT_TYPE = "application/vnd.prose.youtube"
  var FILE_ATTACHMENT_ICON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
    '<path fill-rule="evenodd" d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875Zm5.845 17.03a.75.75 0 0 0 1.06 0l3-3a.75.75 0 1 0-1.06-1.06l-1.72 1.72V12a.75.75 0 0 0-1.5 0v4.19l-1.72-1.72a.75.75 0 0 0-1.06 1.06l3 3Z" clip-rule="evenodd"/>' +
    '<path d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"/>' +
    "</svg>"
  var FILE_PILL_REMOVE_ICON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"/></svg>'

  // Keep in sync with prose.attachment_types (used when building editor allowlist server-side).
  var EXTENSION_TO_MIME = {
    pdf: "application/pdf",
    doc: "application/msword",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xls: "application/vnd.ms-excel",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ppt: "application/vnd.ms-powerpoint",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  }

  var MIME_TYPE_LABELS = {
    "application/pdf": "PDF",
    "application/msword": "Word document",
    "application/vnd.ms-excel": "Excel spreadsheet",
    "application/vnd.ms-powerpoint": "PowerPoint presentation",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel spreadsheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint presentation",
  }

  function decodeHtmlEntities(value) {
    var el = document.createElement("textarea")
    el.innerHTML = value
    return el.value
  }

  function normalizeCaptionText(value) {
    return String(value || "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
  }

  function collectYoutubeCaptionTitles(html) {
    var titles = []
    var seen = {}
    function add(value) {
      var text = normalizeCaptionText(decodeHtmlEntities(value))
      if (text && !seen[text]) {
        seen[text] = true
        titles.push(text)
      }
    }
    if (!html) return titles
    html.replace(/data-prose-caption=(["'])([\s\S]*?)\1/gi, function (_m, _q, value) {
      add(value)
      return _m
    })
    html.replace(/\bcaption=(["'])([\s\S]*?)\1/gi, function (_m, _q, value) {
      add(value)
      return _m
    })
    html.replace(/<textarea\b[^>]*>([\s\S]*?)<\/textarea>/gi, function (_m, value) {
      add(value)
      return _m
    })
    return titles
  }

  function paragraphContainsYoutubeEmbed(paragraph) {
    return /prose-attachment|data-prose-sgid|youtube-nocookie\.com\/embed|attachment--youtube|attachment--embed/i.test(
      paragraph
    )
  }

  function stripYoutubeDuplicateCaptions(html) {
    if (!html) return html
    var titles = collectYoutubeCaptionTitles(html)
    if (!titles.length) return html
    titles.sort(function (a, b) {
      return b.length - a.length
    })

    html = html.replace(/<p\b[^>]*>[\s\S]*?<\/p>/gi, function (paragraph) {
      if (paragraphContainsYoutubeEmbed(paragraph)) return paragraph
      var text = normalizeCaptionText(paragraph)
      for (var i = 0; i < titles.length; i++) {
        if (text === titles[i]) return ""
      }
      return paragraph
    })

    html = html.replace(/<p\b[^>]*>[\s\S]*?<\/p>/gi, function (paragraph) {
      if (!paragraphContainsYoutubeEmbed(paragraph)) return paragraph
      var result = paragraph
      for (var i = 0; i < titles.length; i++) {
        var title = titles[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
        result = result.replace(
          new RegExp(
            "(</prose-attachment>)\\s*(?:<(?:span|strong|em|b|i|br)\\b[^>]*>\\s*)?" +
              title +
              "\\s*(?:</(?:span|strong|em|b|i)>\\s*)?(?=</p>)",
            "i"
          ),
          "$1"
        )
        result = result.replace(
          new RegExp("(</prose-attachment>)\\s*" + title + "\\s*(?=</p>)", "i"),
          "$1"
        )
      }
      return result
    })

    return html
  }

  function applyEditorHtml(editor, html) {
    if (!html) return
    editor.setAttribute("value", stripYoutubeDuplicateCaptions(html))
  }

  function bootstrapInitialValues() {
    document.querySelectorAll("lexxy-editor.django-prose-lexxy").forEach(function (editor) {
      var script = document.getElementById(editor.id + "_initial")
      if (!script || !script.textContent) return
      try {
        var html = JSON.parse(script.textContent)
        if (html) editor.setAttribute("value", stripYoutubeDuplicateCaptions(html))
      } catch (e) {}
    })
  }

  bootstrapInitialValues()

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

  function getCookie(name) {
    var value = "; " + document.cookie
    var parts = value.split("; " + name + "=")
    if (parts.length === 2) return parts.pop().split(";").shift()
    return ""
  }

  function getCsrfToken() {
    var input = document.querySelector("input[name=csrfmiddlewaretoken]")
    if (input && input.value) return input.value
    var meta = document.querySelector('meta[name="csrf-token"]')
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content")
    return getCookie("csrftoken") || ""
  }

  function postJson(url, body, onSuccess, onError) {
    var xhr = new XMLHttpRequest()
    var csrfToken = getCsrfToken()
    xhr.open("POST", url, true)
    xhr.setRequestHeader("Content-Type", "application/json")
    xhr.setRequestHeader("Accept", "application/json")
    if (csrfToken) xhr.setRequestHeader("X-CSRFToken", csrfToken)
    xhr.addEventListener("load", function () {
      if (xhr.status === 201 || xhr.status === 200) {
        try {
          if (typeof onSuccess === "function") onSuccess(JSON.parse(xhr.responseText))
        } catch (e) {
          if (typeof onError === "function") onError(e)
        }
        return
      }
      var message = "Request failed with status " + xhr.status
      try {
        var err = JSON.parse(xhr.responseText)
        if (err && err.error) message = err.error
      } catch (e2) {}
      if (typeof onError === "function") onError(new Error(message))
    })
    xhr.addEventListener("error", function () {
      if (typeof onError === "function") onError(new Error("Network error"))
    })
    xhr.send(JSON.stringify(body))
  }

  function uploadFile(host, file, onSuccess, onError) {
    var formData = new FormData()
    var csrfToken = getCsrfToken()
    formData.append("file", file)
    if (csrfToken) formData.append("csrfmiddlewaretoken", csrfToken)

    var xhr = new XMLHttpRequest()
    xhr.open("POST", host, true)
    if (csrfToken) xhr.setRequestHeader("X-CSRFToken", csrfToken)
    xhr.addEventListener("load", function () {
      if (xhr.status === 201) {
        try {
          var data = JSON.parse(xhr.responseText)
          if (data && data.url && data.sgid) onSuccess(data)
          else if (typeof onError === "function") onError(new Error("Invalid upload response"))
        } catch (e) {
          if (typeof onError === "function") onError(e)
        }
      } else if (typeof onError === "function") {
        onError(new Error("Upload failed with status " + xhr.status))
      }
    })
    xhr.addEventListener("error", function () {
      if (typeof onError === "function") onError(new Error("Network error during upload"))
    })
    xhr.send(formData)
  }

  function attachmentFigureHtml(payload) {
    var ct = escapeHtml(payload.content_type || "")
    var filename = escapeHtml(payload.filename || "file")
    if (payload.kind === "image") {
      return (
        '<figure class="attachment attachment--preview django-prose-attachment django-prose-attachment--image" data-content-type="' +
        ct +
        '"><div class="attachment__container"><img src="' +
        escapeHtml(payload.url) +
        '" alt="' +
        filename +
        '" draggable="false"></div><figcaption class="attachment__caption"><span class="attachment__name">' +
        filename +
        "</span></figcaption></figure>"
      )
    }
    if (payload.kind === "embed" && payload.html) return payload.html
    return filePillFigureHtml(payload)
  }

  function mimeFromFilename(filename) {
    if (!filename || filename.indexOf(".") === -1) return ""
    return EXTENSION_TO_MIME[filename.split(".").pop().toLowerCase()] || ""
  }

  function formatFileTypeLabel(contentType, filename) {
    var ct = (contentType || "").toLowerCase()
    if (MIME_TYPE_LABELS[ct]) return MIME_TYPE_LABELS[ct]
    var inferred = mimeFromFilename(filename)
    if (inferred && MIME_TYPE_LABELS[inferred]) return MIME_TYPE_LABELS[inferred]
    if (ct.indexOf("image/") === 0) return "Image"
    if (ct.indexOf("video/") === 0) return "Video"
    if (ct.indexOf("application/") === 0) {
      var subtype = ct.split("/")[1] || ""
      if (subtype) return subtype.replace(/\./g, " ").replace(/\+/g, " ").replace(/_/g, " ")
      return "Document"
    }
    if (filename && filename.indexOf(".") !== -1) {
      return filename.split(".").pop().toUpperCase() + " file"
    }
    return "File"
  }

  function filePillFigureHtml(payload) {
    var ct = escapeHtml(payload.content_type || "")
    var displayName = escapeHtml(payload.filename || "file")
    var originalName = escapeHtml(payload.original_filename || payload.filename || "file")
    var typeLabel = escapeHtml(formatFileTypeLabel(payload.content_type, payload.filename))
    var href = escapeHtml(payload.download_url || payload.url || "#")
    var sgidAttr = payload.sgid
      ? ' data-prose-sgid="' + escapeHtml(payload.sgid) + '"'
      : ""
    return (
      '<figure class="attachment attachment--file django-prose-attachment django-prose-attachment--file django-prose-file-pill" data-content-type="' +
      ct +
      '"' +
      sgidAttr +
      ' data-prose-filename="' +
      originalName +
      '"><div class="django-prose-file-pill__card"><button type="button" class="django-prose-file-pill__remove" aria-label="Remove attachment" tabindex="-1">' +
      FILE_PILL_REMOVE_ICON_SVG +
      '</button><span class="django-prose-file-pill__icon">' +
      FILE_ATTACHMENT_ICON_SVG +
      '</span><div class="django-prose-file-pill__body"><input type="text" class="django-prose-file-pill__name" value="' +
      displayName +
      '" aria-label="Attachment title" /><span class="django-prose-file-pill__meta"><span class="django-prose-file-pill__filename">' +
      originalName +
      '</span><span class="django-prose-file-pill__type">' +
      typeLabel +
      '</span></span></div><a href="' +
      href +
      '" class="django-prose-file-pill__download" tabindex="-1" aria-hidden="true" download></a></div></figure>'
    )
  }

  function proseAttachmentHtml(payload) {
    if (!payload.sgid) return attachmentFigureHtml(payload)
    var attrs = [
      'sgid="' + escapeHtml(payload.sgid) + '"',
      'content-type="' + escapeHtml(payload.content_type || "") + '"',
      'url="' + escapeHtml(payload.url || "") + '"',
      'filename="' + escapeHtml(payload.filename || "") + '"',
      'filesize="' + escapeHtml(String(payload.size || 0)) + '"',
      'previewable="' + (payload.previewable ? "true" : "false") + '"',
    ]
    if (payload.kind === "embed") {
      attrs.push('presentation="gallery"')
      // YouTube uses content= + figcaption textarea; caption= duplicates plain text in Lexxy.
      if (
        payload.filename &&
        (payload.content_type || "") !== YOUTUBE_CONTENT_TYPE
      ) {
        attrs.push('caption="' + escapeHtml(payload.filename) + '"')
      }
    }
    var inner = payload.html || attachmentFigureHtml(payload)
    return "<prose-attachment " + attrs.join(" ") + ">" + inner + "</prose-attachment>"
  }

  function insertHtmlNow(editorElement, html) {
    if (!html) return

    function appendViaValue() {
      editorElement.value = (editorElement.value || "") + html
    }

    if (!editorElement.contents || typeof editorElement.contents.insertHtml !== "function") {
      appendViaValue()
      return
    }

    if (typeof editorElement.focus === "function") editorElement.focus()

    try {
      editorElement.contents.insertHtml(html)
    } catch (e) {
      appendViaValue()
    }
  }

  function insertHtml(editorElement, html) {
    if (!html) return

    function appendViaValue() {
      editorElement.value = (editorElement.value || "") + html
    }

    if (!editorElement.contents || typeof editorElement.contents.insertHtml !== "function") {
      appendViaValue()
      return
    }

    if (typeof editorElement.focus === "function") editorElement.focus()

    var before = editorElement.value || ""
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        try {
          if (typeof editorElement.focus === "function") editorElement.focus()
          editorElement.contents.insertHtml(html)
        } catch (e) {
          appendViaValue()
          return
        }
        setTimeout(function () {
          if ((editorElement.value || "") === before) appendViaValue()
        }, 50)
      })
    })
  }

  function lexxyYoutubeProseAttachmentHtml(payload) {
    var inner = payload && payload.html
    if (!payload || !payload.sgid || !inner || inner.indexOf("iframe") === -1) return ""

    var attrs = [
      'sgid="' + escapeHtml(payload.sgid) + '"',
      'content-type="' + escapeHtml(payload.content_type || YOUTUBE_CONTENT_TYPE) + '"',
      'content="' + escapeAttributeValue(inner) + '"',
      'url="' + escapeHtml(payload.url || "") + '"',
      'filename="' + escapeHtml(payload.filename || "YouTube video") + '"',
      'filesize="' + escapeHtml(String(payload.size || 0)) + '"',
      'previewable="true"',
      'presentation="gallery"',
    ]
    return "<prose-attachment " + attrs.join(" ") + "></prose-attachment>"
  }

  function insertEmbedViaReplaceLink(editorElement, payload) {
    var contents = editorElement.contents
    var innerHtml = payload && payload.html
    if (
      !contents ||
      !innerHtml ||
      innerHtml.indexOf("iframe") === -1 ||
      typeof contents.replaceNodeWithHTML !== "function"
    ) {
      return false
    }

    var url = (payload && payload.url) || ""
    var attachmentOptions = {
      sgid: payload.sgid,
      contentType: payload.content_type || YOUTUBE_CONTENT_TYPE,
    }

    if (
      editorElement.selection &&
      typeof editorElement.selection.placeCursorAtTheEnd === "function"
    ) {
      editorElement.selection.placeCursorAtTheEnd()
    }

    var nodeKey = null
    if (url && typeof contents.createLink === "function") {
      nodeKey = contents.createLink(url)
    }
    if (!nodeKey) return false

    contents.replaceNodeWithHTML(nodeKey, innerHtml, { attachment: attachmentOptions })
    return true
  }

  function insertEmbed(editorElement, payload) {
    if (!payload || !payload.sgid) return
    if (!payload.html || payload.html.indexOf("iframe") === -1) return

    if (typeof editorElement.focus === "function") editorElement.focus()
    editorElement.cachedValue = null

    function finish() {
      trackSessionUpload(editorElement, payload.sgid)
    }

    if (insertEmbedViaReplaceLink(editorElement, payload)) {
      finish()
      return
    }

    requestAnimationFrame(function () {
      if (insertEmbedViaReplaceLink(editorElement, payload)) {
        finish()
        return
      }

      var html = payload.editor_html || lexxyYoutubeProseAttachmentHtml(payload)
      if (!html) return
      insertHtmlNow(editorElement, html)
      finish()
    })
  }

  function requestEmbed(editorElement, embedHost, url) {
    postJson(
      embedHost,
      { url: url },
      function (data) {
        if (!data || !data.sgid) return
        insertEmbed(editorElement, data)
      },
      function () {}
    )
  }

  function closeLinkDropdown(dropdown) {
    var details = dropdown.closest("details")
    if (details) details.open = false
  }

  function checkEmbeddableUrl(checkHost, url, callback) {
    if (!checkHost || !url) {
      callback(false)
      return null
    }
    var xhr = new XMLHttpRequest()
    var csrfToken = getCsrfToken()
    xhr.open("GET", checkHost + "?url=" + encodeURIComponent(url), true)
    xhr.setRequestHeader("Accept", "application/json")
    if (csrfToken) xhr.setRequestHeader("X-CSRFToken", csrfToken)
    xhr.addEventListener("load", function () {
      if (xhr.status !== 200) {
        callback(false)
        return
      }
      try {
        var data = JSON.parse(xhr.responseText)
        callback(!!(data && data.embeddable))
      } catch (e) {
        callback(false)
      }
    })
    xhr.addEventListener("error", function () {
      callback(false)
    })
    xhr.send()
    return xhr
  }

  function wireLinkEmbedButton(toolbar, editorElement, embedHost, checkHost, attempt) {
    attempt = attempt || 0
    if (!toolbar) {
      toolbar =
        editorElement.toolbarElement || editorElement.querySelector("lexxy-toolbar")
    }
    if (!toolbar) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireLinkEmbedButton(null, editorElement, embedHost, checkHost, attempt + 1)
        })
      }
      return
    }

    var dropdown = toolbar.querySelector("lexxy-link-dropdown")
    if (!dropdown) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireLinkEmbedButton(toolbar, editorElement, embedHost, checkHost, attempt + 1)
        })
      }
      return
    }
    if (dropdown.dataset.djangoProseEmbedWired === "1") return

    var input =
      dropdown.querySelector('input[type="url"]') ||
      dropdown.querySelector("input.input") ||
      dropdown.querySelector("input")
    var actions = dropdown.querySelector(".lexxy-editor__toolbar-dropdown-actions")
    if (!input || !actions) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireLinkEmbedButton(toolbar, editorElement, embedHost, checkHost, attempt + 1)
        })
      }
      return
    }

    dropdown.dataset.djangoProseEmbedWired = "1"

    var embedButton = document.createElement("button")
    embedButton.type = "button"
    embedButton.className = "lexxy-editor__toolbar-button django-prose-embed-button"
    embedButton.textContent = "Embed"
    embedButton.hidden = true
    embedButton.title = "Embed this URL as rich media"
    embedButton.setAttribute("tabindex", "-1")
    // After Link / Unlink so Lexxy tabindex + submit order stay correct.
    actions.appendChild(embedButton)

    var details = dropdown.closest("details")
    var embedCheckTimer = null
    var embedCheckRequest = null

    function updateEmbedButton() {
      embedButton.hidden = true
      actions.classList.remove("django-prose-link-actions--embed")
      if (embedCheckRequest) {
        embedCheckRequest.abort()
        embedCheckRequest = null
      }
      clearTimeout(embedCheckTimer)

      var url = input.value.trim()
      if (!url || !checkHost) return

      embedCheckTimer = setTimeout(function () {
        embedCheckRequest = checkEmbeddableUrl(checkHost, url, function (embeddable) {
          embedCheckRequest = null
          if (input.value.trim() !== url) return
          embedButton.hidden = !embeddable
          actions.classList.toggle("django-prose-link-actions--embed", embeddable)
        })
      }, 300)
    }

    input.addEventListener("input", updateEmbedButton)
    if (details) details.addEventListener("toggle", updateEmbedButton)

    embedButton.addEventListener("click", function (event) {
      event.preventDefault()
      var url = input.value.trim()
      if (!url || embedButton.hidden) return
      closeLinkDropdown(dropdown)
      requestEmbed(editorElement, embedHost, url)
    })
  }

  function patternMatchesMimeType(contentType, pattern) {
    if (!pattern || !contentType) return false
    pattern = String(pattern).toLowerCase()
    contentType = String(contentType).toLowerCase()
    if (pattern === "*/*" || pattern === contentType) return true
    // Wildcards are "type/*" (slash then star). indexOf("*/") does not match "image/*".
    if (pattern.length > 2 && pattern.slice(-2) === "/*") {
      var prefix = pattern.slice(0, -1)
      return contentType.indexOf(prefix) === 0
    }
    return false
  }

  function fileMatchesPermittedTypes(file, permittedTypes) {
    if (!permittedTypes || !permittedTypes.length) return true
    var contentType = ((file && file.type) || "").toLowerCase()
    var inferred = mimeFromFilename(file && file.name)
    var candidates = []
    if (contentType) candidates.push(contentType)
    if (inferred && candidates.indexOf(inferred) === -1) candidates.push(inferred)
    if (!candidates.length) {
      for (var j = 0; j < permittedTypes.length; j++) {
        var open = permittedTypes[j]
        if (open === "application/*" || open === "*/*") return true
      }
      return false
    }
    for (var c = 0; c < candidates.length; c++) {
      for (var i = 0; i < permittedTypes.length; i++) {
        if (patternMatchesMimeType(candidates[c], permittedTypes[i])) return true
      }
    }
    return false
  }

  function permittedTypesForEditor(editorElement) {
    return parsePermittedTypes(editorElement)
  }

  var OFFICE_FILE_EXTENSIONS = ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"

  function buildFileInputAcceptAttribute(editorElement) {
    var permitted = permittedTypesForEditor(editorElement)
    if (!permitted.length) return "*/*"
    var parts = []
    var hasExtension = false
    for (var i = 0; i < permitted.length; i++) {
      var pattern = permitted[i]
      if (!pattern || pattern === YOUTUBE_CONTENT_TYPE) continue
      if (pattern.charAt(0) === ".") {
        parts.push(pattern)
        hasExtension = true
      } else if (pattern.indexOf("/") !== -1) {
        parts.push(pattern)
        if (
          pattern === "application/*" ||
          pattern.indexOf("spreadsheet") !== -1 ||
          pattern.indexOf("wordprocessing") !== -1 ||
          pattern.indexOf("presentation") !== -1 ||
          pattern === "application/pdf"
        ) {
          hasExtension = true
        }
      }
    }
    if (!hasExtension) parts.push(OFFICE_FILE_EXTENSIONS)
    return parts.length ? parts.join(",") : "*/*"
  }

  function djangoPayloadToLexxyBlob(payload) {
    return {
      attachable_sgid: payload.sgid,
      url: payload.download_url || payload.url,
      filename: payload.filename || "file",
      content_type: payload.content_type || "application/octet-stream",
      byte_size: payload.size || 0,
      previewable: true,
      signed_id: payload.sgid || "",
    }
  }

  function insertPendingUpload(editorElement, file) {
    var contents = editorElement.contents
    if (!contents || typeof contents.insertPendingAttachment !== "function") return null
    return contents.insertPendingAttachment(file)
  }

  function completePendingUpload(editorElement, pending, file, payload) {
    if (pending && typeof pending.setAttributes === "function") {
      try {
        pending.setAttributes(djangoPayloadToLexxyBlob(payload))
        if (payload && payload.sgid) trackSessionUpload(editorElement, payload.sgid)
        return
      } catch (e) {
        if (typeof pending.remove === "function") pending.remove()
      }
    }
    insertHtmlNow(editorElement, proseAttachmentHtml(payload))
    if (payload && payload.sgid) trackSessionUpload(editorElement, payload.sgid)
  }

  function uploadFileToEditor(editorElement, host, file, pending) {
    uploadFile(
      host,
      file,
      function (payload) {
        completePendingUpload(editorElement, pending, file, payload)
      },
      function (err) {
        if (pending && typeof pending.remove === "function") pending.remove()
        if (typeof console !== "undefined" && console.error) {
          console.error("django-prose: attachment upload failed", err)
        }
      }
    )
  }

  function uploadFilesToEditor(editorElement, host, files) {
    var fileList = Array.prototype.slice.call(files)

    function uploadNext(index) {
      if (index >= fileList.length) return
      var file = fileList[index]
      var pending = insertPendingUpload(editorElement, file)
      uploadFileToEditor(editorElement, host, file, pending)
      uploadNext(index + 1)
    }

    uploadNext(0)
  }

  function djangoProseEditorFromEvent(event) {
    if (!event) return null

    if (typeof event.composedPath === "function") {
      var path = event.composedPath()
      for (var i = 0; i < path.length; i++) {
        var node = path[i]
        if (
          node &&
          node.nodeType === 1 &&
          node.matches &&
          node.matches("lexxy-editor.django-prose-lexxy")
        ) {
          return node
        }
      }
    }

    if (event.target && event.target.closest) {
      return event.target.closest("lexxy-editor.django-prose-lexxy")
    }

    return null
  }

  function isLexxyInternalDrag(dataTransfer) {
    if (!dataTransfer || !dataTransfer.types) return false
    return Array.prototype.indexOf.call(dataTransfer.types, "application/x-lexxy-node-key") !== -1
  }

  function handleDjangoFileAccept(event) {
    if (event.djangoProseHandled) return

    var editorElement = djangoProseEditorFromEvent(event)
    if (
      !editorElement &&
      event.currentTarget &&
      event.currentTarget.matches &&
      event.currentTarget.matches("lexxy-editor.django-prose-lexxy")
    ) {
      editorElement = event.currentTarget
    }
    if (!editorElement) return

    var host = uploadUrlFromEditor(editorElement)
    if (!host) return

    var file = event.detail && event.detail.file
    if (!file) return

    if (!fileMatchesPermittedTypes(file, permittedTypesForEditor(editorElement))) {
      event.preventDefault()
      return
    }

    event.djangoProseHandled = true
    event.preventDefault()

    // Insert at the current Lexical caret while file-accept is still synchronous
    // (Lexxy has just restored selection after drop).
    var pending = insertPendingUpload(editorElement, file)
    uploadFileToEditor(editorElement, host, file, pending)
  }

  function bindFileUpload(_host, _editorElement) {
    ensureDocumentUploadHandlers()
  }

  function wireFileUploadButton(toolbar, editorElement, host, attempt) {
    attempt = attempt || 0
    if (!toolbar) {
      toolbar =
        editorElement.toolbarElement ||
        editorElement.querySelector("lexxy-toolbar")
    }
    if (!toolbar) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireFileUploadButton(null, editorElement, host, attempt + 1)
        })
      }
      return
    }

    var fileBtn = toolbar.querySelector('button[name="file"]')
    if (!fileBtn) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireFileUploadButton(toolbar, editorElement, host, attempt + 1)
        })
      }
      return
    }

    if (fileBtn._djangoProseFileInput) {
      fileBtn._djangoProseFileInput.remove()
      fileBtn._djangoProseFileInput = null
    }

    var fileInput = document.createElement("input")
    fileInput.type = "file"
    fileInput.multiple = true
    fileInput.accept = buildFileInputAcceptAttribute(editorElement)
    fileInput.style.display = "none"
    fileBtn._djangoProseFileInput = fileInput

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
      uploadFilesToEditor(editorElement, host, fileInput.files)
      fileInput.value = ""
    })

    toolbar.appendChild(fileInput)
  }

  function applyLexxyContentScope(editorElement) {
    var content =
      editorElement.editorContentElement ||
      editorElement.querySelector(".lexxy-editor__content")
    if (content && !content.classList.contains("lexxy-content")) {
      content.classList.add("lexxy-content")
    }
  }

  function handleDjangoEditorDragOver(event) {
    var editorElement = djangoProseEditorFromEvent(event)
    if (!editorElement) return
    var dataTransfer = event.dataTransfer
    if (!dataTransfer || isLexxyInternalDrag(dataTransfer)) return
    if (!uploadUrlFromEditor(editorElement)) return
    if (Array.prototype.indexOf.call(dataTransfer.types, "Files") === -1) return
    event.preventDefault()
    dataTransfer.dropEffect = "copy"
  }

  function proseEditableFromEditor(el) {
    var raw = el.getAttribute("data-prose-editable")
    if (raw == null) return true
    if (raw === "false" || raw === "0") return false
    try {
      return JSON.parse(raw) !== false
    } catch (e) {
      return true
    }
  }

  function applyLexxyEditable(editorElement) {
    if (proseEditableFromEditor(editorElement)) return
    if (!editorElement.editor || typeof editorElement.editor.setEditable !== "function") {
      return
    }
    editorElement.editor.setEditable(false)
    editorElement.classList.add("django-prose-lexxy--readonly")
  }

  function setupDjangoProseEditor(editorElement) {
    applyLexxyContentScope(editorElement)
    applyLexxyEditable(editorElement)
    wireEditorFormSubmit(editorElement)
    var uploadHost = uploadUrlFromEditor(editorElement)
    if (uploadHost) {
      bindFileUpload(uploadHost, editorElement)
      wireFileUploadButton(null, editorElement, uploadHost)
    }
    var embedHost = embedUrlFromEditor(editorElement)
    var checkHost = embedCheckUrlFromEditor(editorElement)
    if (embedHost && checkHost) {
      wireLinkEmbedButton(null, editorElement, embedHost, checkHost)
    }
    var captionHost = captionUrlFromEditor(editorElement)
    if (captionHost) {
      wireYoutubeCaptions(editorElement, captionHost)
      wireFileAttachmentPills(editorElement, captionHost)
    }
  }

  var djangoProseUploadHandlersBound = false
  function ensureDocumentUploadHandlers() {
    if (djangoProseUploadHandlersBound) return
    djangoProseUploadHandlersBound = true
    document.addEventListener("lexxy:file-accept", handleDjangoFileAccept, true)
    document.addEventListener("dragover", handleDjangoEditorDragOver, true)
  }

  function uploadUrlFromEditor(el) {
    return el.dataset.uploadAttachmentUrl || el.getAttribute("data-upload-attachment-url") || ""
  }

  function embedUrlFromEditor(el) {
    return el.dataset.embedUrl || el.getAttribute("data-embed-url") || ""
  }

  function embedCheckUrlFromEditor(el) {
    return el.dataset.embedCheckUrl || el.getAttribute("data-embed-check-url") || ""
  }

  function captionUrlFromEditor(el) {
    return el.dataset.captionUrl || el.getAttribute("data-caption-url") || ""
  }

  var YOUTUBE_CAPTION_TEXTAREA_SELECTOR =
    "figure.attachment--youtube figcaption textarea, figure.attachment--youtube .django-prose-youtube-caption__input"

  function isYoutubeCaptionTextarea(node) {
    if (!node || !node.closest) return false
    return !!node.closest("figure.attachment--youtube figcaption")
  }

  function collectQueryRoots(node, roots) {
    if (!node || roots.indexOf(node) !== -1) return
    roots.push(node)
    if (node.shadowRoot) collectQueryRoots(node.shadowRoot, roots)
    var children = node.children || []
    for (var i = 0; i < children.length; i++) {
      if (children[i].shadowRoot) collectQueryRoots(children[i].shadowRoot, roots)
    }
  }

  function queryYoutubeCaptionTextareas(editorElement) {
    var roots = []
    collectQueryRoots(editorElement, roots)
    var seen = []
    var textareas = []
    roots.forEach(function (root) {
      if (!root.querySelectorAll) return
      root.querySelectorAll(YOUTUBE_CAPTION_TEXTAREA_SELECTOR).forEach(function (textarea) {
        if (seen.indexOf(textarea) === -1) {
          seen.push(textarea)
          textareas.push(textarea)
        }
      })
    })
    return textareas
  }

  function resolveYoutubeCaptionSgid(textarea) {
    var figure = textarea.closest("figure[data-prose-sgid]")
    if (figure) {
      var fromFigure = figure.getAttribute("data-prose-sgid")
      if (fromFigure) return fromFigure
    }
    var attachment = textarea.closest("prose-attachment")
    if (attachment) {
      var fromTag = attachment.getAttribute("sgid")
      if (fromTag) return fromTag
    }
    return ""
  }

  function resolveYoutubeCaptionFigure(textarea) {
    return textarea.closest("figure.attachment--youtube")
  }

  function initialYoutubeCaption(textarea) {
    var figure = resolveYoutubeCaptionFigure(textarea)
    if (!figure) return ""
    return (figure.getAttribute("data-prose-caption") || "").trim()
  }

  function escapeAttributeValue(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
  }

  function youtubeFigureContentHtml(figure, caption) {
    var clone = figure.cloneNode(true)
    if (caption) {
      clone.setAttribute("data-prose-caption", caption)
    } else {
      clone.removeAttribute("data-prose-caption")
    }
    var textarea = clone.querySelector("textarea")
    if (textarea) textarea.textContent = ""
    return clone.outerHTML
  }

  function updateProseAttachmentContentInHtml(html, sgid, innerHtml) {
    if (!html || !sgid) return html
    var tagPattern = new RegExp(
      "<prose-attachment\\b([^>]*\\bsgid=[\"']" +
        sgid.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
        "[\"'][^>]*)>\\s*</prose-attachment>",
      "gi"
    )
    return html.replace(tagPattern, function (_match, attrs) {
      var cleaned = attrs.replace(/\scontent=(["'])(?:\\.|(?!\1)[\s\S])*\1/i, "")
      return (
        "<prose-attachment" +
        cleaned +
        ' content="' +
        escapeAttributeValue(innerHtml) +
        '"></prose-attachment>'
      )
    })
  }

  function setEditorFormValue(editorElement, html, options) {
    options = options || {}
    if (options.allowValueReset) {
      editorElement.cachedValue = null
      editorElement.value = html
    } else if (html) {
      editorElement.cachedValue = html
    }
    if (editorElement.internals && typeof editorElement.internals.setFormValue === "function") {
      editorElement.internals.setFormValue(html)
      if ("_internalFormValue" in editorElement) editorElement._internalFormValue = html
      return
    }
  }

  function getSessionUploadSgids(editorElement) {
    try {
      var parsed = JSON.parse(editorElement.dataset.djangoProseSessionUploads || "[]")
      return Array.isArray(parsed) ? parsed : []
    } catch (e) {
      return []
    }
  }

  function trackSessionUpload(editorElement, sgid) {
    if (!sgid) return
    var list = getSessionUploadSgids(editorElement)
    if (list.indexOf(sgid) === -1) list.push(sgid)
    editorElement.dataset.djangoProseSessionUploads = JSON.stringify(list)
  }

  function extractSgidsFromHtml(html) {
    if (!html) return []
    var sgids = []
    var prosePattern = /<prose-attachment\b[^>]*\ssgid=["']([^"']+)["']/gi
    var dataPattern = /data-prose-sgid=["']([^"']+)["']/gi
    var match
    while ((match = prosePattern.exec(html)) !== null) sgids.push(match[1])
    while ((match = dataPattern.exec(html)) !== null) sgids.push(match[1])
    return sgids.filter(function (sgid, index, list) {
      return list.indexOf(sgid) === index
    })
  }

  function collectAttachmentSgidsFromDom(editorElement) {
    var sgids = []
    editorElement.querySelectorAll("prose-attachment[sgid]").forEach(function (node) {
      var sgid = node.getAttribute("sgid")
      if (sgid) sgids.push(sgid)
    })
    editorElement.querySelectorAll("figure[data-prose-sgid]").forEach(function (node) {
      var sgid = node.getAttribute("data-prose-sgid")
      if (sgid) sgids.push(sgid)
    })
    return sgids.filter(function (sgid, index, list) {
      return list.indexOf(sgid) === index
    })
  }

  function flushEditorValueForSubmit(editorElement) {
    syncYoutubeCaptionsToEditorValue(editorElement)
    var html = editorElement.cachedValue || editorElement.value || ""
    setEditorFormValue(editorElement, html, { allowValueReset: true })
    return html
  }

  function computeSessionAbandonedSgids(editorElement) {
    var domSgids = collectAttachmentSgidsFromDom(editorElement)
    var valueSgids = extractSgidsFromHtml(editorElement.value || "")
    return getSessionUploadSgids(editorElement).filter(function (sgid) {
      return domSgids.indexOf(sgid) === -1 && valueSgids.indexOf(sgid) === -1
    })
  }

  function prepareEditorForSave(editorElement) {
    var captionHost = captionUrlFromEditor(editorElement)
    if (captionHost) {
      // Sync from live textareas before any Lexxy value reload; allowValueReset in
      // flushEditorValueForSubmit reparses the DOM and would leave textareas empty
      // if we saved captions after that reload.
      syncYoutubeCaptionsToEditorValue(editorElement)
      queryYoutubeCaptionTextareas(editorElement).forEach(function (textarea) {
        saveYoutubeCaption(textarea, captionHost)
      })
    }

    flushEditorValueForSubmit(editorElement)
    var abandoned = computeSessionAbandonedSgids(editorElement)
    var fieldName = editorElement.getAttribute("name")
    var editorId = editorElement.id
    if (fieldName && editorId) {
      var hidden = document.getElementById(editorId + "_prose_abandoned_sgids")
      if (hidden) hidden.value = JSON.stringify(abandoned)
    }
  }

  function wireEditorFormSubmit(editorElement) {
    var form = editorElement.form || editorElement.closest("form")
    if (!form) return
    if (form.dataset.djangoProseEditorSubmit === "1") return
    form.dataset.djangoProseEditorSubmit = "1"
    form.addEventListener(
      "submit",
      function () {
        form.querySelectorAll("lexxy-editor.django-prose-lexxy").forEach(function (editor) {
          prepareEditorForSave(editor)
        })
      },
      true
    )
  }

  function syncYoutubeCaptionsToEditorValue(editorElement, options) {
    var html = editorElement.value || ""
    if (!html) return false

    var changed = false
    queryYoutubeCaptionTextareas(editorElement).forEach(function (textarea) {
      var sgid = resolveYoutubeCaptionSgid(textarea)
      var figure = resolveYoutubeCaptionFigure(textarea)
      if (!sgid || !figure) return
      var innerHtml = youtubeFigureContentHtml(figure, textarea.value.trim())
      var patched = updateProseAttachmentContentInHtml(html, sgid, innerHtml)
      if (patched !== html) {
        html = patched
        changed = true
      }
    })

    if (changed) {
      setEditorFormValue(editorElement, stripYoutubeDuplicateCaptions(html), options)
    }
    return changed
  }

  function isolateCaptionFromLexxy(editorElement) {
    if (editorElement.dataset.djangoProseCaptionIsolate === "1") return
    editorElement.dataset.djangoProseCaptionIsolate = "1"

    editorElement.addEventListener(
      "keydown",
      function (event) {
        if (!isYoutubeCaptionTextarea(event.target)) return
        if (event.key !== "Enter") return
        event.stopImmediatePropagation()
      },
      true
    )

    editorElement.addEventListener(
      "mousedown",
      function (event) {
        if (!isYoutubeCaptionTextarea(event.target)) return
        event.stopPropagation()
      },
      true
    )

    editorElement.addEventListener(
      "click",
      function (event) {
        if (!isYoutubeCaptionTextarea(event.target)) return
        event.stopPropagation()
      },
      true
    )
  }

  function resizeCaptionInput(textarea) {
    textarea.style.height = "auto"
    textarea.style.height = textarea.scrollHeight + "px"
  }

  function saveYoutubeCaption(textarea, captionHost) {
    if (!captionHost) return
    var sgid = resolveYoutubeCaptionSgid(textarea)
    if (!sgid) return
    var caption = textarea.value.trim()
    var lastSaved = textarea.dataset.djangoProseCaptionSaved || ""
    if (caption === lastSaved) return

    postJson(
      captionHost,
      { sgid: sgid, caption: caption },
      function () {
        textarea.dataset.djangoProseCaptionSaved = caption
      },
      function () {}
    )
  }

  function bindYoutubeCaptionTextarea(textarea, captionHost, editorElement) {
    if (textarea.dataset.djangoProseCaptionBound === "1") return
    textarea.dataset.djangoProseCaptionBound = "1"
    textarea.classList.add("django-prose-youtube-caption__input")
    textarea.removeAttribute("readonly")
    textarea.removeAttribute("disabled")
    if (!textarea.value.trim()) {
      var initialCaption = initialYoutubeCaption(textarea)
      if (initialCaption) textarea.value = initialCaption
    }
    textarea.dataset.djangoProseCaptionSaved = textarea.value.trim()
    resizeCaptionInput(textarea)

    textarea.addEventListener("input", function () {
      resizeCaptionInput(textarea)
      var figure = resolveYoutubeCaptionFigure(textarea)
      if (!figure) return
      var value = textarea.value.trim()
      if (value) figure.setAttribute("data-prose-caption", value)
      else figure.removeAttribute("data-prose-caption")
    })
    textarea.addEventListener("blur", function () {
      saveYoutubeCaption(textarea, captionHost)
      syncYoutubeCaptionsToEditorValue(editorElement)
    })
    textarea.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault()
        event.stopPropagation()
        textarea.blur()
        return
      }
      // Lexxy ActionTextAttachmentNode stops all keydown from reaching Lexical;
      // without this, Backspace/typing are handled by the editor instead of the textarea.
      event.stopPropagation()
    })
    ;["copy", "cut", "paste"].forEach(function (type) {
      textarea.addEventListener(type, function (event) {
        event.stopPropagation()
      })
    })
  }

  function wireYoutubeCaptions(editorElement, captionHost) {
    if (!captionHost) return

    isolateCaptionFromLexxy(editorElement)

    function bindAll() {
      queryYoutubeCaptionTextareas(editorElement).forEach(function (textarea) {
        bindYoutubeCaptionTextarea(textarea, captionHost, editorElement)
      })
    }

    if (editorElement.dataset.djangoProseCaptionWired === "1") {
      bindAll()
      return
    }
    editorElement.dataset.djangoProseCaptionWired = "1"

    editorElement.addEventListener("lexxy:initialize", bindAll)
    editorElement.addEventListener("lexxy:change", bindAll)

    if (typeof MutationObserver !== "undefined") {
      var observer = new MutationObserver(function () {
        bindAll()
      })
      observer.observe(editorElement, { childList: true, subtree: true })
    }

    wireEditorFormSubmit(editorElement)

    bindAll()
  }

  var FILE_PILL_NAME_INPUT_SELECTOR =
    "figure.django-prose-file-pill .django-prose-file-pill__name"

  function isFilePillNameInput(node) {
    if (!node || !node.closest) return false
    return !!node.closest("figure.django-prose-file-pill")
  }

  function queryFilePillNameInputs(editorElement) {
    var roots = []
    collectQueryRoots(editorElement, roots)
    var seen = []
    var inputs = []
    roots.forEach(function (root) {
      if (!root.querySelectorAll) return
      root.querySelectorAll(FILE_PILL_NAME_INPUT_SELECTOR).forEach(function (input) {
        if (seen.indexOf(input) === -1) {
          seen.push(input)
          inputs.push(input)
        }
      })
    })
    return inputs
  }

  function resolveFilePillSgid(node) {
    var figure = node.closest("figure[data-prose-sgid]")
    if (figure) {
      var fromFigure = figure.getAttribute("data-prose-sgid")
      if (fromFigure) return fromFigure
    }
    var attachment = node.closest("prose-attachment")
    if (attachment) {
      var fromTag = attachment.getAttribute("sgid")
      if (fromTag) return fromTag
    }
    return ""
  }

  function clickLexxyAttachmentDelete(host) {
    if (!host) return false
    var deleteHost = host.querySelector("lexxy-node-delete-button")
    if (!deleteHost) return false
    var btn = deleteHost.querySelector("button.lexxy-node-delete")
    if (!btn) return false
    var prevPointerEvents = deleteHost.style.pointerEvents
    var prevDisplay = deleteHost.style.display
    deleteHost.style.pointerEvents = "auto"
    deleteHost.style.display = "block"
    btn.click()
    deleteHost.style.pointerEvents = prevPointerEvents
    deleteHost.style.display = prevDisplay
    return true
  }

  function resolveAttachmentSgid(node) {
    var sgid = resolveFilePillSgid(node)
    if (sgid) return sgid
    var attachment = node.closest("prose-attachment")
    if (attachment) return attachment.getAttribute("sgid") || ""
    var figure = node.closest("figure[data-prose-sgid]")
    if (figure) return figure.getAttribute("data-prose-sgid") || ""
    return ""
  }

  function purgeAttachmentFromEditorValue(editorElement, sgid) {
    if (!sgid || !editorElement) return false
    var html = editorElement.value || ""
    if (!html || html.indexOf(sgid) === -1) return false

    var escaped = sgid.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    var next = html
    next = next.replace(
      new RegExp(
        "<prose-attachment\\b[^>]*\\ssgid=[\"']" + escaped + "[\"'][^>]*>\\s*</prose-attachment>",
        "gi"
      ),
      ""
    )
    next = next.replace(
      new RegExp(
        "<prose-attachment\\b[^>]*\\ssgid=[\"']" + escaped + "[\"'][^>]*/?>",
        "gi"
      ),
      ""
    )
    next = next.replace(
      new RegExp(
        "<figure\\b[^>]*\\bdata-prose-sgid=[\"']" + escaped + "[\"'][^>]*>.*?</figure>",
        "gi"
      ),
      ""
    )
    if (next === html) return false
    setEditorFormValue(editorElement, stripYoutubeDuplicateCaptions(next), {
      allowValueReset: true,
    })
    return true
  }

  function removeProseAttachmentFrom(node) {
    var editorElement = node.closest("lexxy-editor.django-prose-lexxy")
    var sgid = resolveAttachmentSgid(node)
    var attachmentHost = node.closest("prose-attachment")
    var figure = node.closest(
      "figure.attachment, figure.django-prose-file-pill, figure[data-prose-sgid]"
    )
    var lexxyClicked = false

    if (attachmentHost && clickLexxyAttachmentDelete(attachmentHost)) {
      lexxyClicked = true
    }
    if (!lexxyClicked && figure) {
      if (clickLexxyAttachmentDelete(figure)) lexxyClicked = true
      else {
        var hostFromFigure = figure.closest("prose-attachment")
        if (hostFromFigure && clickLexxyAttachmentDelete(hostFromFigure)) {
          lexxyClicked = true
        }
      }
    }

    function finishRemove() {
      var valueHasSgid =
        sgid && editorElement && (editorElement.value || "").indexOf(sgid) !== -1
      if (valueHasSgid && editorElement) {
        purgeAttachmentFromEditorValue(editorElement, sgid)
      }
      if (editorElement && typeof editorElement.focus === "function") editorElement.focus()
    }

    if (lexxyClicked) {
      requestAnimationFrame(function () {
        requestAnimationFrame(finishRemove)
      })
      return
    }

    if (sgid && editorElement) purgeAttachmentFromEditorValue(editorElement, sgid)
    finishRemove()
  }

  function saveFilePillName(input, captionHost) {
    if (!captionHost) return
    var sgid = resolveFilePillSgid(input)
    if (!sgid) return
    var caption = input.value.trim()
    var lastSaved = input.dataset.djangoProseCaptionSaved || ""
    if (caption === lastSaved) return

    postJson(
      captionHost,
      { sgid: sgid, caption: caption },
      function () {
        input.dataset.djangoProseCaptionSaved = caption
      },
      function () {}
    )
  }

  function bindFilePillNameInput(input, captionHost) {
    if (input.dataset.djangoProseFilePillBound === "1") return
    input.dataset.djangoProseFilePillBound = "1"
    input.dataset.djangoProseCaptionSaved = input.value.trim()

    input.addEventListener("blur", function () {
      saveFilePillName(input, captionHost)
    })
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault()
        event.stopPropagation()
        input.blur()
      }
    })
  }

  function bindFilePillRemoveButton(button) {
    if (button.dataset.djangoProseFilePillRemoveBound === "1") return
    button.dataset.djangoProseFilePillRemoveBound = "1"
    button.addEventListener("click", function (event) {
      event.preventDefault()
      event.stopPropagation()
      removeProseAttachmentFrom(button)
    })
  }

  function bindFilePillControls(root, captionHost) {
    if (!root.querySelectorAll) return
    root.querySelectorAll(FILE_PILL_NAME_INPUT_SELECTOR).forEach(function (input) {
      bindFilePillNameInput(input, captionHost)
    })
    root.querySelectorAll("figure.django-prose-file-pill .django-prose-file-pill__remove").forEach(
      bindFilePillRemoveButton
    )
  }

  function isolateFilePillsFromLexxy(editorElement) {
    if (editorElement.dataset.djangoProseFilePillIsolate === "1") return
    editorElement.dataset.djangoProseFilePillIsolate = "1"

    editorElement.addEventListener(
      "mousedown",
      function (event) {
        if (isFilePillNameInput(event.target) || event.target.closest(".django-prose-file-pill__remove")) {
          event.stopPropagation()
        }
      },
      true
    )
    editorElement.addEventListener(
      "click",
      function (event) {
        if (isFilePillNameInput(event.target) || event.target.closest(".django-prose-file-pill__remove")) {
          event.stopPropagation()
        }
      },
      true
    )
  }

  function wireFileAttachmentPills(editorElement, captionHost) {
    if (!captionHost) return

    isolateFilePillsFromLexxy(editorElement)

    function bindAll() {
      var roots = []
      collectQueryRoots(editorElement, roots)
      roots.forEach(function (root) {
        bindFilePillControls(root, captionHost)
      })
    }

    if (editorElement.dataset.djangoProseFilePillWired === "1") {
      bindAll()
      return
    }
    editorElement.dataset.djangoProseFilePillWired = "1"

    editorElement.addEventListener("lexxy:initialize", bindAll)
    editorElement.addEventListener("lexxy:change", bindAll)

    if (typeof MutationObserver !== "undefined") {
      var observer = new MutationObserver(bindAll)
      observer.observe(editorElement, { childList: true, subtree: true })
    }

    bindAll()
  }

  function parsePermittedTypes(el) {
    var raw = el.getAttribute("data-permitted-attachment-types")
    if (raw == null) {
      raw = el.dataset.permittedAttachmentTypes || ""
    }
    if (!raw) return []
    raw = String(raw).trim()
    if (!raw) return []
    if (raw.charAt(0) === "[" || raw.charAt(0) === "{") {
      try {
        var parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          return parsed.filter(function (item) {
            return item && String(item).trim()
          })
        }
      } catch (e) {}
    }
    return raw.split(/[\s,]+/).filter(function (item) {
      return item && String(item).trim()
    })
  }

  import(LEXXY_MODULE)
    .then(function (Lexxy) {
      if (!Lexxy || typeof Lexxy.configure !== "function" || !Lexxy.Extension) return

      var YOUTUBE_SANITIZER_ELEMENTS = [
        "figure",
        "figcaption",
        "div",
        "iframe",
        "textarea",
        {
          tag: "iframe",
          attributes: [
            "src",
            "title",
            "allow",
            "allowfullscreen",
            "referrerpolicy",
            "loading",
            "width",
            "height",
            "frameborder",
          ],
        },
        {
          tag: "figure",
          attributes: ["class", "data-prose-sgid", "data-prose-content-type", "data-prose-caption"],
        },
        { tag: "div", attributes: ["class"] },
        {
          tag: "textarea",
          attributes: ["class", "rows", "placeholder", "readonly"],
        },
        { tag: "figcaption", attributes: ["class"] },
      ]

      class DjangoProseExtension extends Lexxy.Extension {
        get enabled() {
          return !!(
            uploadUrlFromEditor(this.editorElement) ||
            embedUrlFromEditor(this.editorElement) ||
            captionUrlFromEditor(this.editorElement)
          )
        }

        get allowedElements() {
          if (!embedUrlFromEditor(this.editorElement)) return []
          return YOUTUBE_SANITIZER_ELEMENTS
        }

        constructor(editorElement) {
          super(editorElement)
          setupDjangoProseEditor(editorElement)
          editorElement.addEventListener("lexxy:initialize", function () {
            setupDjangoProseEditor(editorElement)
            applyLexxyEditable(editorElement)
            var current = editorElement.getAttribute("value")
            if (!current) return
            var stripped = stripYoutubeDuplicateCaptions(current)
            if (stripped !== current) applyEditorHtml(editorElement, stripped)
          })
        }

        initializeToolbar(toolbar) {
          var uploadHost = uploadUrlFromEditor(this.editorElement)
          var embedHost = embedUrlFromEditor(this.editorElement)
          var checkHost = embedCheckUrlFromEditor(this.editorElement)
          if (uploadHost) wireFileUploadButton(toolbar, this.editorElement, uploadHost)
          if (embedHost && checkHost) {
            wireLinkEmbedButton(toolbar, this.editorElement, embedHost, checkHost)
          }
        }
      }

      ensureDocumentUploadHandlers()

      function deepMergeLexxyConfig(target, source) {
        if (!source || typeof source !== "object") return target
        for (var key in source) {
          if (!Object.prototype.hasOwnProperty.call(source, key)) continue
          var value = source[key]
          if (
            value &&
            typeof value === "object" &&
            !Array.isArray(value) &&
            target[key] &&
            typeof target[key] === "object" &&
            !Array.isArray(target[key])
          ) {
            deepMergeLexxyConfig(target[key], value)
          } else {
            target[key] = value
          }
        }
        return target
      }

      function proseLexxyConfigureFromSettings() {
        var script = document.getElementById("prose-lexxy-configure")
        if (!script || !script.textContent) return {}
        try {
          return JSON.parse(script.textContent)
        } catch (e) {
          return {}
        }
      }

      var lexxyConfigure = {
        global: {
          attachmentTagName: "prose-attachment",
          attachmentContentTypeNamespace: "prose",
          extensions: [DjangoProseExtension],
        },
        default: {
          attachments: true,
          toolbar: { upload: "file" },
          // Lexxy 0.9.14 matches MIME types literally; django-prose validates in
          // lexxy:file-accept (wildcards supported) via handleDjangoFileAccept.
          permittedAttachmentTypes: null,
        },
      }
      deepMergeLexxyConfig(lexxyConfigure, proseLexxyConfigureFromSettings())
      lexxyConfigure.global.attachmentTagName = "prose-attachment"
      lexxyConfigure.global.attachmentContentTypeNamespace = "prose"
      lexxyConfigure.global.extensions = [DjangoProseExtension]

      Lexxy.configure(lexxyConfigure)

      bootstrapInitialValues()

      document.querySelectorAll("lexxy-editor.django-prose-lexxy").forEach(function (el) {
        setupDjangoProseEditor(el)
        el.addEventListener("lexxy:initialize", function () {
          setupDjangoProseEditor(el)
        })
      })
    })
    .catch(function (err) {
      if (typeof console !== "undefined" && console.error) {
        console.error("django-prose: failed to load Lexxy from " + LEXXY_MODULE, err)
      }
    })
})()
