(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var navigation = document.getElementById("nav2");
    if (!navigation) return;
    navigation.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest("a[href^='#']");
      if (!link) return;
      var destination = document.querySelector(link.getAttribute("href"));
      if (!destination) return;
      event.preventDefault();
      window.scrollTo({ top: Math.max(0, destination.getBoundingClientRect().top + window.scrollY - navigation.offsetHeight - 8), behavior: "smooth" });
    });
  });
})();
