"""mkdocs-macros module for the ITS Standard Extracts site.

Ports the production ISO-TC204 site behaviour: automatically inject a
standard-metadata box (name + Published/Edition/Pages + annotation) at the top
of every extract page. Extract pages are identified by a ``standard`` key in
their YAML front matter.

This replaces the old mdbook ``frontmatter_preprocessor.py``.
"""


def on_pre_page_macros(env):
    """Inject the metadata box before Jinja2 processes an extract page."""
    if "standard" in env.page.meta and "render_standard_metadata" not in env.markdown:
        env.markdown = "{{ render_standard_metadata() }}\n\n" + env.markdown


def define_env(env):
    @env.macro
    def render_standard_metadata(meta=None):
        """Render a metadata box for a standard extract from page front matter."""
        if meta is None:
            meta = env.page.meta
        if not meta:
            return ""

        html = f'<p><strong><em>{meta.get("name", "")}</em></strong></p>\n'
        html += (
            '<div class="standard-metadata" style="'
            "background-color: #f8f9fa; "
            "padding: 0.75em 1.1em; "
            "margin-top: 0.3em; "
            "margin-bottom: 1em; "
            "border-left: 4px solid #3f51b5; "
            'border-radius: 4px;"><small>\n'
        )

        for label, value in (
            ("Published", meta.get("published")),
            ("Edition", meta.get("edition")),
            ("Pages", meta.get("pages")),
        ):
            if value:
                html += f"  <strong>{label}:</strong> {value}<br>\n"

        if meta.get("annotation"):
            html += f'  {meta.get("annotation")}\n'

        html += "</small></div>"
        return html
