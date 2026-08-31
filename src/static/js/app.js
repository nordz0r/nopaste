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
                const text = await res.text();
                const version = cfg.assetVersion || "";
                try {
                    await loadScript(`/static/js/marked.min.js?v=${version}`);
                } catch (err) {
                    /* fall through to textContent */
                }
                if (mdEl && window.marked) {
                    marked.setOptions({ gfm: true, breaks: false });
                    mdEl.innerHTML = sanitizeRenderedHtml(marked.parse(text));
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
