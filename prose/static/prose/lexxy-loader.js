;(function () {
  var LEXXY_MODULE = "https://esm.sh/@37signals/lexxy@0.9.0-beta"
  var YOUTUBE_CONTENT_TYPE = "application/vnd.prose.youtube"
  var FILE_ATTACHMENT_ICON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
    '<path fill-rule="evenodd" d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875Zm5.845 17.03a.75.75 0 0 0 1.06 0l3-3a.75.75 0 1 0-1.06-1.06l-1.72 1.72V12a.75.75 0 0 0-1.5 0v4.19l-1.72-1.72a.75.75 0 0 0-1.06 1.06l3 3Z" clip-rule="evenodd"/>' +
    '<path d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"/>' +
    "</svg>"

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
    var href = escapeHtml(payload.download_url || payload.url)
    return (
      '<figure class="attachment attachment--file django-prose-attachment django-prose-attachment--file" data-content-type="' +
      ct +
      '"><span class="attachment__icon">' +
      FILE_ATTACHMENT_ICON_SVG +
      '</span><figcaption class="attachment__caption"><a href="' +
      href +
      '" class="attachment__name">' +
      filename +
      '</a><span class="attachment__size">' +
      escapeHtml(formatSize(payload.size || 0)) +
      "</span></figcaption></figure>"
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

  function insertEmbed(editorElement, payload) {
    var html = payload && payload.html
    if (!html || !payload.sgid || html.indexOf("iframe") === -1) return

    var contents = editorElement.contents
    if (!contents || typeof contents.replaceNodeWithHTML !== "function") {
      insertHtml(editorElement, html)
      return
    }

    var url = payload.url || ""
    if (!url) return

    if (typeof editorElement.focus === "function") editorElement.focus()

    function replacePlaceholderLink() {
      var nodeKey = contents.createLink(url)
      if (
        !nodeKey &&
        editorElement.selection &&
        typeof editorElement.selection.placeCursorAtTheEnd === "function"
      ) {
        editorElement.selection.placeCursorAtTheEnd()
        nodeKey = contents.createLink(url)
      }
      if (nodeKey) {
        contents.replaceNodeWithHTML(nodeKey, html, {
          attachment: {
            sgid: payload.sgid,
            contentType: payload.content_type || YOUTUBE_CONTENT_TYPE,
          },
        })
      }
    }

    requestAnimationFrame(replacePlaceholderLink)
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
    dropdown.dataset.djangoProseEmbedWired = "1"

    var input = dropdown.querySelector('input[type="url"]')
    var actions = dropdown.querySelector(".lexxy-editor__toolbar-dropdown-actions")
    if (!input || !actions) return

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

  function bindFileUpload(host, editorElement) {
    if (editorElement.dataset.djangoProseFileUploadBound === "1") return
    editorElement.dataset.djangoProseFileUploadBound = "1"

    editorElement.addEventListener(
      "lexxy:file-accept",
      function (e) {
        e.preventDefault()
        var file = e.detail && e.detail.file
        if (!file) return
        uploadFile(
          host,
          file,
          function (payload) {
            insertHtml(editorElement, proseAttachmentHtml(payload))
          },
          function () {}
        )
      },
      true
    )
  }

  function wireFileUploadButton(toolbar, editorElement, host, attempt) {
    attempt = attempt || 0
    var fileBtn = toolbar.querySelector('button[name="file"]')
    if (!fileBtn) {
      if (attempt < 30) {
        requestAnimationFrame(function () {
          wireFileUploadButton(toolbar, editorElement, host, attempt + 1)
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
      Array.prototype.forEach.call(fileInput.files, function (file) {
        uploadFile(
          host,
          file,
          function (payload) {
            insertHtml(editorElement, proseAttachmentHtml(payload))
          },
          function () {}
        )
      })
      fileInput.value = ""
    })

    toolbar.appendChild(fileInput)
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
    editorElement.cachedValue = null
    if (editorElement.internals && typeof editorElement.internals.setFormValue === "function") {
      editorElement.internals.setFormValue(html)
      if ("_internalFormValue" in editorElement) editorElement._internalFormValue = html
      return
    }
    if (options.allowValueReset) editorElement.value = html
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

    if (changed) setEditorFormValue(editorElement, stripYoutubeDuplicateCaptions(html), options)
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
    if (!textarea.value.trim()) {
      var initialCaption = initialYoutubeCaption(textarea)
      if (initialCaption) textarea.value = initialCaption
    }
    textarea.dataset.djangoProseCaptionSaved = textarea.value.trim()
    resizeCaptionInput(textarea)

    textarea.addEventListener("input", function () {
      resizeCaptionInput(textarea)
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
      }
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

    var form = editorElement.form || editorElement.closest("form")
    if (form && form.dataset.djangoProseCaptionSubmit !== "1") {
      form.dataset.djangoProseCaptionSubmit = "1"
      form.addEventListener(
        "submit",
        function () {
          syncYoutubeCaptionsToEditorValue(editorElement, { allowValueReset: true })
          queryYoutubeCaptionTextareas(editorElement).forEach(function (textarea) {
            saveYoutubeCaption(textarea, captionHost)
          })
        },
        true
      )
    }

    bindAll()
  }

  function parsePermittedTypes(el) {
    var raw = el.dataset.permittedAttachmentTypes || el.getAttribute("data-permitted-attachment-types") || ""
    if (!raw) return null
    try {
      return JSON.parse(raw)
    } catch (e) {
      return null
    }
  }

  import(LEXXY_MODULE)
    .then(function (Lexxy) {
      if (!Lexxy || typeof Lexxy.configure !== "function" || !Lexxy.Extension) return

      class DjangoProseExtension extends Lexxy.Extension {
        get enabled() {
          return !!(
            uploadUrlFromEditor(this.editorElement) ||
            embedUrlFromEditor(this.editorElement) ||
            captionUrlFromEditor(this.editorElement)
          )
        }

        constructor(editorElement) {
          super(editorElement)
          var uploadHost = uploadUrlFromEditor(editorElement)
          var captionHost = captionUrlFromEditor(editorElement)
          if (uploadHost) bindFileUpload(uploadHost, editorElement)
          if (captionHost) wireYoutubeCaptions(editorElement, captionHost)
          editorElement.addEventListener("lexxy:initialize", function () {
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

      Lexxy.configure({
        global: {
          attachmentTagName: "prose-attachment",
          attachmentContentTypeNamespace: "prose",
          extensions: [DjangoProseExtension],
        },
        default: {
          attachments: true,
          toolbar: { upload: "file" },
          permittedAttachmentTypes: [
            "image/*",
            "video/*",
            "application/*",
            YOUTUBE_CONTENT_TYPE,
          ],
        },
      })

      bootstrapInitialValues()

      document.querySelectorAll("lexxy-editor.django-prose-lexxy").forEach(function (el) {
        var permitted = parsePermittedTypes(el)
        if (permitted && permitted.length) {
          el.setAttribute("permitted-attachment-types", permitted.join(","))
        }
      })
    })
    .catch(function () {})
})()
