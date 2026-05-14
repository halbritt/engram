(function () {
  "use strict";

  function isTextEntry(element) {
    if (!element) {
      return false;
    }
    var tagName = element.tagName;
    return (
      tagName === "INPUT" ||
      tagName === "TEXTAREA" ||
      tagName === "SELECT" ||
      element.isContentEditable === true
    );
  }

  function focusQueueFilter() {
    var filter = document.getElementById("queue-filter");
    if (filter && typeof filter.focus === "function") {
      filter.focus();
    }
  }

  document.addEventListener("keydown", function (event) {
    if (isTextEntry(document.activeElement)) {
      return;
    }
    if (event.key === "/" && !event.shiftKey) {
      event.preventDefault();
      focusQueueFilter();
    }
  });

  document.addEventListener("input", function (event) {
    if (event.target.id !== "queue-filter") {
      return;
    }
    var needle = event.target.value.toLowerCase();
    document.querySelectorAll("tbody tr").forEach(function (row) {
      row.hidden = needle !== "" && !row.textContent.toLowerCase().includes(needle);
    });
  });
})();
