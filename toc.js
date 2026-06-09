// Populate the sidebar
//
// This is a script, and not included directly in the page, to control the total size of the book.
// The TOC contains an entry for each page, so if each page includes a copy of the TOC,
// the total size of the page becomes O(n**2).
class MDBookSidebarScrollbox extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        this.innerHTML = '<ol class="chapter"><li class="chapter-item expanded affix "><a href="index.html">Overview</a></li><li class="chapter-item expanded "><a href="CEN_TS_16157-13/index.html">CEN/TS 16157-13</a></li><li class="chapter-item expanded "><a href="EN_18052/index.html">EN 18052</a></li><li class="chapter-item expanded "><a href="EN_ISO_12855/index.html">EN ISO 12855</a></li><li class="chapter-item expanded "><a href="EN_ISO_14906/index.html">EN ISO 14906</a></li><li class="chapter-item expanded "><a href="EN_ISO_17573-1/index.html">EN ISO 17573-1</a></li><li class="chapter-item expanded "><a href="ISO_4448-1/index.html">ISO/TR 4448-1</a></li><li class="chapter-item expanded "><a href="ISO_14823-1/index.html">ISO 14823-1</a></li><li class="chapter-item expanded "><a href="ISO_15622/index.html">ISO 15622</a></li><li class="chapter-item expanded "><a href="ISO_17748-3/index.html">ISO 17748-3</a></li><li class="chapter-item expanded "><a href="ISO_21214/index.html">ISO 21214</a></li><li class="chapter-item expanded "><a href="ISO_23792-1/index.html">ISO 23792-1</a></li><li class="chapter-item expanded "><a href="ISO_26683-2/index.html">ISO 26683-2</a></li><li class="chapter-item expanded "><a href="ISO_TS_19091/index.html">ISO/TS 19091</a></li><li class="chapter-item expanded "><a href="ISO_TS_22726-1/index.html">ISO/TS 22726-1</a></li><li class="chapter-item expanded "><a href="ISO_TS_22741-10/index.html">ISO/TS 22741-10</a></li></ol>';
        // Set the current, active page, and reveal it if it's hidden
        let current_page = document.location.href.toString().split("#")[0].split("?")[0];
        if (current_page.endsWith("/")) {
            current_page += "index.html";
        }
        var links = Array.prototype.slice.call(this.querySelectorAll("a"));
        var l = links.length;
        for (var i = 0; i < l; ++i) {
            var link = links[i];
            var href = link.getAttribute("href");
            if (href && !href.startsWith("#") && !/^(?:[a-z+]+:)?\/\//.test(href)) {
                link.href = path_to_root + href;
            }
            // The "index" page is supposed to alias the first chapter in the book.
            if (link.href === current_page || (i === 0 && path_to_root === "" && current_page.endsWith("/index.html"))) {
                link.classList.add("active");
                var parent = link.parentElement;
                if (parent && parent.classList.contains("chapter-item")) {
                    parent.classList.add("expanded");
                }
                while (parent) {
                    if (parent.tagName === "LI" && parent.previousElementSibling) {
                        if (parent.previousElementSibling.classList.contains("chapter-item")) {
                            parent.previousElementSibling.classList.add("expanded");
                        }
                    }
                    parent = parent.parentElement;
                }
            }
        }
        // Track and set sidebar scroll position
        this.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                sessionStorage.setItem('sidebar-scroll', this.scrollTop);
            }
        }, { passive: true });
        var sidebarScrollTop = sessionStorage.getItem('sidebar-scroll');
        sessionStorage.removeItem('sidebar-scroll');
        if (sidebarScrollTop) {
            // preserve sidebar scroll position when navigating via links within sidebar
            this.scrollTop = sidebarScrollTop;
        } else {
            // scroll sidebar to current active section when navigating via "next/previous chapter" buttons
            var activeSection = document.querySelector('#sidebar .active');
            if (activeSection) {
                activeSection.scrollIntoView({ block: 'center' });
            }
        }
        // Toggle buttons
        var sidebarAnchorToggles = document.querySelectorAll('#sidebar a.toggle');
        function toggleSection(ev) {
            ev.currentTarget.parentElement.classList.toggle('expanded');
        }
        Array.from(sidebarAnchorToggles).forEach(function (el) {
            el.addEventListener('click', toggleSection);
        });
    }
}
window.customElements.define("mdbook-sidebar-scrollbox", MDBookSidebarScrollbox);
