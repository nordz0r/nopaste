(function () {
    const cfg = window.NOPASTE || { i18n: {}, changelog: {}, theme: {} };
    const i18n = cfg.i18n || {};
    const scriptPromises = {};

    function loadScript(src) {
        if (scriptPromises[src]) return scriptPromises[src];
        scriptPromises[src] = new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) {
                resolve();
                return;
            }
            const script = document.createElement("script");
            script.src = src;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
        });
        return scriptPromises[src];
    }

    window.nopasteLoadScript = loadScript;

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/static/sw.js", { scope: "/static/" }).catch(() => {});
        });
    }

    const feedbackLink = document.getElementById("footer-feedback");
    if (feedbackLink && feedbackLink.href) {
        try {
            const feedbackUrl = new URL(feedbackLink.href);
            const extra = [
                `- Theme: \`${document.documentElement.getAttribute("data-theme") || "dark"}\``,
                `- User-Agent: \`${navigator.userAgent}\``,
            ].join("\n");
            const currentBody = feedbackUrl.searchParams.get("body") || "";
            feedbackUrl.searchParams.set("body", `${currentBody.replace(/\s*$/, "")}\n${extra}\n`);
            feedbackLink.href = feedbackUrl.toString();
        } catch (err) {
            /* keep the server-rendered URL */
        }
    }

    const footer = document.querySelector(".site-footer");
    if (footer) {
        const BOTTOM_THRESHOLD_PX = 24;
        function updateFooterVisibility() {
            const doc = document.documentElement;
            const scrollable = doc.scrollHeight > window.innerHeight + 4;
            if (!scrollable) {
                footer.classList.remove("is-hidden");
                return;
            }
            const atTop = window.scrollY <= 2;
            const atBottom =
                window.innerHeight + window.scrollY >= doc.scrollHeight - BOTTOM_THRESHOLD_PX;
            if (atTop || atBottom) {
                footer.classList.remove("is-hidden");
            } else {
                footer.classList.add("is-hidden");
            }
        }
        window.addEventListener("scroll", updateFooterVisibility, { passive: true });
        window.addEventListener("resize", updateFooterVisibility, { passive: true });
        updateFooterVisibility();
    }

    const header = document.querySelector(".site-header");
    if (header) {
        let lastScrollY = window.scrollY;
        const HIDE_THRESHOLD = 180;
        window.addEventListener(
            "scroll",
            () => {
                const currentScrollY = window.scrollY;
                if (currentScrollY > HIDE_THRESHOLD && currentScrollY > lastScrollY) {
                    header.classList.add("is-hidden");
                } else if (currentScrollY < lastScrollY || currentScrollY <= HIDE_THRESHOLD) {
                    header.classList.remove("is-hidden");
                }
                lastScrollY = currentScrollY;
            },
            { passive: true }
        );
    }

    function showNotification(message) {
        const notification = document.getElementById("notification");
        if (!notification) return;
        notification.textContent = message;
        notification.style.display = "block";
        setTimeout(() => {
            notification.style.opacity = "0";
            setTimeout(() => {
                notification.style.display = "none";
                notification.style.opacity = "1";
            }, 300);
        }, 2000);
    }

    async function copyToClipboard(text, successMsg) {
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand("copy");
                document.body.removeChild(textArea);
            }
            showNotification(successMsg || i18n["toast.copied"] || "Copied!");
        } catch (err) {
            showNotification(i18n["toast.copy_error"] || "Copy failed");
        }
    }

    function flashPress(btn) {
        if (!btn) return;
        btn.classList.add("is-pressed");
        window.setTimeout(() => btn.classList.remove("is-pressed"), 180);
    }

    window.showNotification = showNotification;
    window.copyToClipboard = copyToClipboard;
    window.flashPress = flashPress;

    function burstConfetti(originEl) {
        const fire = window.confetti;
        if (typeof fire !== "function") return;
        let origin = { y: 0.7 };
        if (originEl && typeof originEl.getBoundingClientRect === "function") {
            const rect = originEl.getBoundingClientRect();
            const vw = Math.max(window.innerWidth || 1, 1);
            const vh = Math.max(window.innerHeight || 1, 1);
            origin = {
                x: (rect.left + rect.width / 2) / vw,
                y: (rect.top + rect.height / 2) / vh,
            };
        }
        fire({
            particleCount: 90,
            spread: 70,
            startVelocity: 38,
            origin,
            disableForReducedMotion: true,
        });
    }
    window.nopasteBurstConfetti = burstConfetti;

    window.nopasteFavoriteIcons = {
        heart: "/static/images/heart.png",
        gray: "/static/images/heart_gray.png",
        broken: "/static/images/heart_broken.png",
    };

    function setFavoriteHeartVisual(button, state) {
        const icons = window.nopasteFavoriteIcons;
        const img = button
            ? button.querySelector(".favorite-heart")
            : null;
        if (button) {
            button.classList.toggle("is-favorited", state === "on");
            button.classList.toggle("is-breaking", state === "breaking");
        }
        if (!img) return;
        if (state === "on") img.src = icons.heart;
        else if (state === "breaking") img.src = icons.broken;
        else img.src = icons.gray;
    }

    function showBrokenThenGrayHeart(img, button) {
        if (button && button._heartTimer) {
            window.clearTimeout(button._heartTimer);
            button._heartTimer = null;
        }
        setFavoriteHeartVisual(button, "breaking");
        if (!button) {
            if (img) img.src = window.nopasteFavoriteIcons.broken;
            return;
        }
        button._heartTimer = window.setTimeout(function () {
            button._heartTimer = null;
            setFavoriteHeartVisual(button, "off");
        }, 700);
    }
    window.setFavoriteHeartVisual = setFavoriteHeartVisual;
    window.showBrokenThenGrayHeart = showBrokenThenGrayHeart;

    const copyBtn = document.getElementById("copy-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            flashPress(copyBtn);
            const target =
                typeof shareUrl !== "undefined" && shareUrl
                    ? shareUrl
                    : cfg.shortUrl || window.location.href;
            copyToClipboard(target, i18n["toast.link_copied"] || "Link copied!");
        });
    }

    const copyContentBtn = document.getElementById("copy-content-btn");
    if (copyContentBtn) {
        copyContentBtn.addEventListener("click", () => flashPress(copyContentBtn));
    }

    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    if (themeToggleBtn) {
        const sunIcon = themeToggleBtn.querySelector(".theme-icon-sun");
        const moonIcon = themeToggleBtn.querySelector(".theme-icon-moon");
        const labels = cfg.theme || {};

        function updateToggleIcons(currentTheme) {
            if (currentTheme === "light") {
                if (sunIcon) sunIcon.style.display = "none";
                if (moonIcon) moonIcon.style.display = "inline-block";
                themeToggleBtn.setAttribute(
                    "title",
                    labels.toDark || "Switch to dark theme"
                );
            } else {
                if (sunIcon) sunIcon.style.display = "inline-block";
                if (moonIcon) moonIcon.style.display = "none";
                themeToggleBtn.setAttribute(
                    "title",
                    labels.toLight || "Switch to light theme"
                );
            }
        }

        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        updateToggleIcons(currentTheme);

        themeToggleBtn.addEventListener("click", () => {
            const activeTheme =
                document.documentElement.getAttribute("data-theme") === "light"
                    ? "dark"
                    : "light";
            document.documentElement.setAttribute("data-theme", activeTheme);
            localStorage.setItem("nopaste-theme", activeTheme);
            updateToggleIcons(activeTheme);
        });
    }
    function attachTableEnhancements(root) {
        if (!root || typeof root.querySelectorAll !== "function") return;
        const lblFilter = i18n["table.filter_col"] || "Filter";
        const lblAll = i18n["table.filter_all"] || "(All)";
        const lblSearch = i18n["table.filter_search"] || "Search…";
        const lblClear = i18n["table.filter_clear"] || "Clear";

        root.querySelectorAll(".table-wrap").forEach((wrap) => {
            const table = wrap.querySelector("table");
            if (!table) return;
            const thead = table.querySelector("thead");
            const tbody = table.querySelector("tbody");
            if (!thead || !tbody) return;
            const ths = Array.from(thead.querySelectorAll("th"));
            const rows = Array.from(tbody.querySelectorAll("tr"));
            // Add Excel-like filter to columns if the table has >= 3 rows
            if (rows.length < 3 || ths.length === 0) return;

            // State for this table: Map<colIndex, Set<selectedValues> | null>
            const activeFilters = new Map();

            function applyFilters() {
                rows.forEach((row) => {
                    const cells = row.children;
                    let show = true;
                    for (const [colIdx, selectedSet] of activeFilters.entries()) {
                        if (!selectedSet || selectedSet.size === 0) continue;
                        const cell = cells[colIdx];
                        const val = cell ? cell.textContent.trim() : "";
                        if (!selectedSet.has(val)) {
                            show = false;
                            break;
                        }
                    }
                    row.classList.toggle("is-filtered-out", !show);
                });
            }

            let openDropdown = null;
            let activeBtn = null;

            function closeCurrentDropdown() {
                if (openDropdown) {
                    openDropdown.remove();
                    openDropdown = null;
                }
                if (activeBtn) {
                    activeBtn.classList.remove("is-open");
                    activeBtn = null;
                }
            }

            // Close dropdown on click outside or escape
            document.addEventListener("click", (e) => {
                if (openDropdown && !openDropdown.contains(e.target) && (!activeBtn || !activeBtn.contains(e.target))) {
                    closeCurrentDropdown();
                }
            });
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && openDropdown) {
                    closeCurrentDropdown();
                }
            });
            wrap.addEventListener("scroll", closeCurrentDropdown, { passive: true });

            ths.forEach((th, colIdx) => {
                if (th.querySelector(".th-filter-btn")) return;

                // Wrap th inner content in .th-content for flex layout
                const originalNodes = Array.from(th.childNodes);
                const contentWrap = document.createElement("span");
                contentWrap.className = "th-content";
                const labelSpan = document.createElement("span");
                labelSpan.className = "th-label";
                originalNodes.forEach((node) => labelSpan.appendChild(node));
                contentWrap.appendChild(labelSpan);

                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "th-filter-btn";
                btn.title = lblFilter;
                btn.setAttribute("aria-label", lblFilter);
                btn.innerHTML = '<svg viewBox="0 0 16 16"><path d="M1.5 2.5h13l-5.2 6.1v4.9l-2.6-1.5v-3.4L1.5 2.5z"/></svg>';
                contentWrap.appendChild(btn);

                th.innerHTML = "";
                th.appendChild(contentWrap);

                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (openDropdown && activeBtn === btn) {
                        closeCurrentDropdown();
                        return;
                    }
                    closeCurrentDropdown();

                    // Extract unique non-empty values for this column across all rows
                    const counts = new Map();
                    rows.forEach((row) => {
                        const cell = row.children[colIdx];
                        const val = cell ? cell.textContent.trim() : "";
                        counts.set(val, (counts.get(val) || 0) + 1);
                    });
                    const uniqueVals = Array.from(counts.keys()).sort();

                    const dd = document.createElement("div");
                    dd.className = "th-filter-dropdown";

                    // Positioning: fixed relative to button
                    const rect = btn.getBoundingClientRect();
                    const ddWidth = Math.min(240, window.innerWidth - 16);
                    let left = rect.left;
                    if (left + ddWidth > window.innerWidth - 8) {
                        left = Math.max(8, window.innerWidth - ddWidth - 8);
                    }
                    let top = rect.bottom + 4;
                    if (top + 240 > window.innerHeight && rect.top > 250) {
                        top = rect.top - 244;
                    }
                    dd.style.left = `${Math.round(left)}px`;
                    dd.style.top = `${Math.round(top)}px`;
                    dd.style.width = `${Math.round(ddWidth)}px`;

                    // Search input if > 5 values
                    let searchInput = null;
                    if (uniqueVals.length > 5) {
                        searchInput = document.createElement("input");
                        searchInput.type = "search";
                        searchInput.className = "th-filter-search";
                        searchInput.placeholder = lblSearch;
                        searchInput.setAttribute("aria-label", lblSearch);
                        dd.appendChild(searchInput);
                    }

                    const list = document.createElement("ul");
                    list.className = "th-filter-list";

                    // Option: (All)
                    const currentFilter = activeFilters.get(colIdx) || null;
                    const allItem = document.createElement("li");
                    allItem.className = "th-filter-item";
                    allItem.innerHTML = `<label style="display:flex;align-items:center;gap:0.4rem;width:100%;cursor:pointer;"><input type="radio" name="th_filter_${colIdx}" ${!currentFilter ? "checked" : ""}> <span>${lblAll}</span></label>`;
                    allItem.addEventListener("click", (evt) => {
                        evt.stopPropagation();
                        activeFilters.delete(colIdx);
                        btn.classList.remove("is-active");
                        applyFilters();
                        closeCurrentDropdown();
                    });
                    list.appendChild(allItem);

                    uniqueVals.forEach((val) => {
                        const item = document.createElement("li");
                        item.className = "th-filter-item";
                        const isChecked = currentFilter && currentFilter.has(val) && currentFilter.size === 1;
                        const displayVal = val || "—";
                        item.innerHTML = `<label style="display:flex;align-items:center;gap:0.4rem;width:100%;cursor:pointer;"><input type="radio" name="th_filter_${colIdx}" ${isChecked ? "checked" : ""}> <span>${displayVal} (${counts.get(val)})</span></label>`;
                        item.addEventListener("click", (evt) => {
                            evt.stopPropagation();
                            activeFilters.set(colIdx, new Set([val]));
                            btn.classList.add("is-active");
                            applyFilters();
                            closeCurrentDropdown();
                        });
                        list.appendChild(item);
                    });
                    dd.appendChild(list);

                    if (searchInput) {
                        searchInput.addEventListener("input", () => {
                            const q = searchInput.value.trim().toLowerCase();
                            Array.from(list.children).forEach((li, idx) => {
                                if (idx === 0) return; // keep (All) visible
                                const text = li.textContent.toLowerCase();
                                li.style.display = (!q || text.includes(q)) ? "" : "none";
                            });
                        });
                    }

                    // Clear filter footer action if active
                    if (currentFilter) {
                        const actions = document.createElement("div");
                        actions.className = "th-filter-actions";
                        const clearBtn = document.createElement("button");
                        clearBtn.type = "button";
                        clearBtn.className = "th-filter-clear-btn";
                        clearBtn.textContent = lblClear;
                        clearBtn.addEventListener("click", (evt) => {
                            evt.stopPropagation();
                            activeFilters.delete(colIdx);
                            btn.classList.remove("is-active");
                            applyFilters();
                            closeCurrentDropdown();
                        });
                        actions.appendChild(clearBtn);
                        dd.appendChild(actions);
                    }

                    document.body.appendChild(dd);
                    openDropdown = dd;
                    activeBtn = btn;
                    btn.classList.add("is-open");
                    if (searchInput) searchInput.focus();
                });
            });
        });
    }
    window.nopasteAttachTableEnhancements = attachTableEnhancements;


    (function initChangelogModal() {
        const modal = document.getElementById("changelog-modal");
        const openBtn = document.getElementById("open-changelog-btn");
        const closeBtn = document.getElementById("changelog-modal-close");
        const statusEl = document.getElementById("changelog-modal-status");
        const mdEl = document.getElementById("changelog-modal-markdown");
        if (!modal) return;

        let loaded = false;
        let loading = false;
        const msgLoading = (cfg.changelog && cfg.changelog.loading) || "Loading…";
        const msgError = (cfg.changelog && cfg.changelog.error) || "Could not load changelog";

        function sanitizeRenderedHtml(html) {
            const template = document.createElement("template");
            template.innerHTML = html;
            template.content
                .querySelectorAll("script, iframe, object, embed, link, meta")
                .forEach((node) => node.remove());
            template.content.querySelectorAll("*").forEach((el) => {
                [...el.attributes].forEach((attr) => {
                    const name = attr.name.toLowerCase();
                    const value = attr.value || "";
                    if (name.startsWith("on") || value.trim().toLowerCase().startsWith("javascript:")) {
                        el.removeAttribute(attr.name);
                    }
                });
            });
            return template.innerHTML;
        }

        async function ensureLoaded() {
            if (loaded || loading) return;
            loading = true;
            if (statusEl) {
                statusEl.hidden = false;
                statusEl.textContent = msgLoading;
            }
            if (mdEl) mdEl.hidden = true;
            try {
                const res = await fetch("/api/changelog", {
                    headers: { Accept: "text/markdown, text/plain" },
                });
                if (!res.ok) throw new Error("bad status");
                let text = await res.text();
                if (text.includes("<!-- version list -->")) {
                    text = text.slice(text.indexOf("<!-- version list -->") + "<!-- version list -->".length).trim();
                } else if (text.startsWith("# Changelog")) {
                    const match = text.search(/^##\s+/m);
                    if (match !== -1) {
                        text = text.slice(match).trim();
                    }
                }
                const version = cfg.assetVersion || "";
                try {
                    await loadScript(`/static/js/marked.min.js?v=${version}`);
                } catch (err) {
                    /* fall through to textContent */
                }
                if (mdEl && window.marked) {
                    const renderer = new marked.Renderer();
                    const defaultTable = renderer.table.bind(renderer);
                    renderer.table = function(header, body) {
                        const rendered = typeof header === "object" && header !== null
                            ? defaultTable(header)
                            : defaultTable(header, body);
                        return `<div class="table-wrap">${rendered}</div>`;
                    };
                    marked.setOptions({ renderer, gfm: true, breaks: false });
                    mdEl.innerHTML = sanitizeRenderedHtml(marked.parse(text));
                    attachTableEnhancements(mdEl);
                    mdEl.hidden = false;
                    if (statusEl) statusEl.hidden = true;
                } else if (mdEl) {
                    mdEl.textContent = text;
                    mdEl.hidden = false;
                    if (statusEl) statusEl.hidden = true;
                }
                loaded = true;
            } catch (err) {
                if (statusEl) {
                    statusEl.hidden = false;
                    statusEl.textContent = msgError;
                }
            } finally {
                loading = false;
            }
        }

        function openModal() {
            modal.hidden = false;
            void modal.offsetWidth;
            modal.classList.add("is-open");
            document.body.classList.add("modal-open");
            ensureLoaded();
            if (closeBtn) closeBtn.focus();
        }

        function closeModal() {
            modal.classList.remove("is-open");
            document.body.classList.remove("modal-open");
            window.setTimeout(() => {
                if (!modal.classList.contains("is-open")) modal.hidden = true;
            }, 160);
            if (window.location.hash === "#changelog") {
                history.replaceState(null, "", window.location.pathname + window.location.search);
            }
        }

        if (openBtn) {
            openBtn.addEventListener("click", (e) => {
                e.preventDefault();
                openModal();
            });
        }
        if (closeBtn) closeBtn.addEventListener("click", closeModal);

        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeModal();
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && modal.classList.contains("is-open")) {
                e.preventDefault();
                closeModal();
            }
        });

        function maybeOpenFromHash() {
            if (window.location.hash === "#changelog") openModal();
        }
        window.addEventListener("hashchange", maybeOpenFromHash);
        maybeOpenFromHash();
    })();
})();
