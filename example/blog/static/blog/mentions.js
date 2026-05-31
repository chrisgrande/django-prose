(function () {
  "use strict"

  var MENTION_AVATAR_SELECTOR = ".mention-pill--editor .mention-pill__avatar--control"

  function clickLexxyAttachmentDelete(host) {
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

  function bindMentionAvatar(avatar) {
    if (avatar.dataset.mentionDeleteBound === "1") return
    avatar.dataset.mentionDeleteBound = "1"

    avatar.addEventListener(
      "mousedown",
      function (event) {
        var attachment = avatar.closest("prose-attachment")
        if (attachment && attachment.classList.contains("node--selected")) {
          event.preventDefault()
          event.stopPropagation()
        }
      },
      true
    )

    avatar.addEventListener("click", function (event) {
      var attachment = avatar.closest("prose-attachment")
      if (!attachment || !attachment.classList.contains("node--selected")) return
      event.preventDefault()
      event.stopPropagation()
      clickLexxyAttachmentDelete(attachment)
    })
  }

  function bindMentions(root) {
    if (!root || !root.querySelectorAll) return
    root.querySelectorAll(MENTION_AVATAR_SELECTOR).forEach(bindMentionAvatar)
  }

  function wireMentionPills(editorElement) {
    function bindAll() {
      bindMentions(editorElement)
      var content = editorElement.querySelector(".lexxy-editor__content")
      if (content) bindMentions(content)
    }

    if (editorElement.dataset.mentionPillWired === "1") {
      bindAll()
      return
    }
    editorElement.dataset.mentionPillWired = "1"

    editorElement.addEventListener("lexxy:initialize", bindAll)
    editorElement.addEventListener("lexxy:change", bindAll)

    if (typeof MutationObserver !== "undefined") {
      var observer = new MutationObserver(bindAll)
      observer.observe(editorElement, { childList: true, subtree: true })
    }

    bindAll()
  }

  function init() {
    document.querySelectorAll("lexxy-editor.django-prose-lexxy").forEach(function (el) {
      wireMentionPills(el)
      el.addEventListener("lexxy:initialize", function () {
        wireMentionPills(el)
      })
    })
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init)
  } else {
    init()
  }
})()
