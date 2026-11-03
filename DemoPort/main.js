(function () {
  "use strict";

  var P = window.PROFILE;
  var FIELD_NAMES = {};
  P.fields.forEach(function (f) { FIELD_NAMES[f.id] = f.title; });

  function $(sel) { return document.querySelector(sel); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fill(sel, html) { var el = $(sel); if (el) el.innerHTML = html; }

  // 공통: 이름·문구 바인딩, 이메일, 연도, 테마
  document.querySelectorAll("[data-bind]").forEach(function (el) {
    var v = P[el.dataset.bind];
    if (v != null) el.innerHTML = esc(v).replace(/\n/g, "<br>");
  });

  var email = P.email.user + "@" + P.email.domain;
  document.querySelectorAll("[data-email]").forEach(function (el) { el.textContent = email; });
  document.querySelectorAll("[data-email-link]").forEach(function (el) { el.href = "mailto:" + email; });

  var year = $("#year");
  if (year) year.textContent = new Date().getFullYear();

  document.querySelectorAll(".theme-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.dataset.theme ||
        (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  });

  // 모바일 메뉴
  var toggle = $(".nav-toggle");
  var menu = $("#nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      toggle.setAttribute("aria-label", open ? "메뉴 열기" : "메뉴 닫기");
      menu.classList.toggle("open", !open);
    });
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        menu.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  function projectCard(p) {
    return '<a class="project-card" href="project.html?id=' + encodeURIComponent(p.id) + '" data-field="' + esc(p.field) + '">' +
      '<span class="tag">' + esc(FIELD_NAMES[p.field] || "") + "</span>" +
      "<h3>" + esc(p.title) + "</h3>" +
      '<p class="meta">' + esc(p.period) + " · " + esc(p.role) + "</p>" +
      "<p>" + esc(p.summary) + "</p>" +
      '<ul class="mini-stats">' + p.outcomes.slice(0, 2).map(function (o) {
        return "<li><strong>" + esc(o.value) + "</strong><span>" + esc(o.label) + "</span></li>";
      }).join("") + "</ul>" +
      '<span class="more">자세히 보기 →</span></a>';
  }

  // 메인 페이지
  if ($("#project-list")) {
    fill("#stats", P.stats.map(function (s) {
      return "<li><strong>" + esc(s.value) + "</strong><span>" + esc(s.label) + "</span></li>";
    }).join(""));

    fill("#keywords", P.keywords.map(function (k) { return "<li>#" + esc(k) + "</li>"; }).join(""));

    fill("#values", P.values.map(function (v, i) {
      return '<li><span class="num">0' + (i + 1) + "</span><div><h3>" + esc(v.title) + "</h3><p>" + esc(v.desc) + "</p></div></li>";
    }).join(""));

    fill("#field-list", P.fields.map(function (f) {
      return '<div class="card field-card"><h3>' + esc(f.title) + "</h3><p>" + esc(f.desc) + "</p><ul>" +
        f.items.map(function (it) { return "<li>" + esc(it) + "</li>"; }).join("") + "</ul></div>";
    }).join(""));

    fill("#timeline", P.experience.map(function (x) {
      return '<li><p class="period">' + esc(x.period) + "</p><h3>" + esc(x.org) + '</h3><p class="meta">' + esc(x.role) + "</p><ul>" +
        x.tasks.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul></li>";
    }).join(""));

    var filterDefs = [{ id: "all", title: "전체" }].concat(P.fields);
    fill("#filters", filterDefs.map(function (f, i) {
      return '<button type="button" class="filter' + (i === 0 ? " active" : "") + '" data-filter="' + esc(f.id) +
        '" aria-pressed="' + (i === 0) + '">' + esc(f.title) + "</button>";
    }).join(""));

    var list = $("#project-list");
    function renderProjects(field) {
      var items = P.projects.filter(function (p) { return field === "all" || p.field === field; });
      list.innerHTML = items.length ? items.map(projectCard).join("") : '<p class="empty">해당 분야의 프로젝트가 아직 없습니다.</p>';
    }
    renderProjects("all");

    $("#filters").addEventListener("click", function (e) {
      var btn = e.target.closest(".filter");
      if (!btn) return;
      document.querySelectorAll(".filter").forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("active", on);
        b.setAttribute("aria-pressed", String(on));
      });
      renderProjects(btn.dataset.filter);
    });

    fill("#skill-groups", P.skills.map(function (g) {
      return '<div class="skill-group"><h3>' + esc(g.group) + '</h3><ul class="chips">' +
        g.items.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ul></div>";
    }).join(""));

    fill("#cert-list", P.certifications.map(function (c) {
      return '<li><span class="year">' + esc(c.year) + "</span><div><strong>" + esc(c.name) + "</strong><span>" + esc(c.issuer) + "</span></div></li>";
    }).join(""));

    var copyBtn = $("#copy-email");
    var status = $("#copy-status");
    copyBtn.addEventListener("click", function () {
      function done() { status.textContent = "이메일 주소를 복사했습니다."; }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(email).then(done, fallback);
      } else {
        fallback();
      }
      function fallback() {
        var ta = document.createElement("textarea");
        ta.value = email;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); done(); } catch (e) { status.textContent = email; }
        ta.remove();
      }
    });
  }

  // 프로젝트 상세 페이지
  var detail = $("#project-detail");
  if (detail) {
    var id = new URLSearchParams(location.search).get("id");
    var p = P.projects.filter(function (x) { return x.id === id; })[0];
    if (!p) {
      detail.innerHTML = '<h1>프로젝트를 찾을 수 없습니다</h1><p><a href="index.html#projects">프로젝트 목록으로 돌아가기</a></p>';
      return;
    }
    document.title = p.title + " | " + P.name;

    var idx = P.projects.indexOf(p);
    var next = P.projects[(idx + 1) % P.projects.length];

    detail.innerHTML =
      '<span class="tag">' + esc(FIELD_NAMES[p.field] || "") + "</span>" +
      '<h1 class="detail-title">' + esc(p.title) + "</h1>" +
      '<p class="lead">' + esc(p.summary) + "</p>" +
      '<dl class="facts">' +
        "<div><dt>기간</dt><dd>" + esc(p.period) + "</dd></div>" +
        "<div><dt>역할</dt><dd>" + esc(p.role) + "</dd></div>" +
        "<div><dt>협력 기관</dt><dd>" + esc(p.partner) + "</dd></div>" +
        "<div><dt>대상</dt><dd>" + esc(p.target) + "</dd></div>" +
      "</dl>" +
      '<ul class="stats stats-detail">' + p.outcomes.map(function (o) {
        return "<li><strong>" + esc(o.value) + "</strong><span>" + esc(o.label) + "</span></li>";
      }).join("") + "</ul>" +
      '<section><h2>배경 및 문제 정의</h2><p>' + esc(p.background) + "</p></section>" +
      "<section><h2>목표</h2><p>" + esc(p.goal) + "</p></section>" +
      '<section><h2>기획 · 실행 과정</h2><ol class="steps">' +
        p.process.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ol></section>" +
      '<section><h2>변화 사례</h2><blockquote>' + esc(p.story) + "</blockquote></section>" +
      "<section><h2>배운 점 · 후속 과제</h2><p>" + esc(p.lessons) + "</p></section>" +
      '<p class="privacy-note">※ 사업 참여자의 개인정보 보호를 위해 이름, 얼굴 등 식별 정보는 공개하지 않습니다.</p>' +
      '<nav class="detail-nav"><a class="btn btn-ghost" href="index.html#projects">← 목록으로</a>' +
      (next !== p ? '<a class="btn btn-primary" href="project.html?id=' + encodeURIComponent(next.id) + '">다음 프로젝트 →</a>' : "") +
      "</nav>";
  }
})();
