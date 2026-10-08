from kneekura_web.html_inspector import in_scope_links, inspect_html


def test_extract_observations():
    html = (
        '<html><head><title> Sample Page </title><meta name="description" content="Info">'
        '<link rel="stylesheet" href="/site.css"></head><body>'
        '<h1>Hello <em>World</em></h1><a href="/docs">Docs</a>'
        '<img src="/a.png" alt="A"><form action="/send" method="post"></form>'
        '<script src="/a.js">not a paragraph</script><p>Real body.</p></body></html>'
    )
    found = inspect_html(html)
    assert found["title"] == "Sample Page"
    assert found["headings"] == [{"level": 1, "text": "Hello World"}]
    assert found["description"] == "Info"
    assert found["stylesheets"] == ["/site.css"]
    assert found["scripts"] == ["/a.js"]
    assert found["forms"] == [{"method": "POST", "action": "/send"}]
    assert "not a paragraph" not in found["text_excerpt"]
    assert "Real body." in found["text_excerpt"]


def test_link_scope():
    links = [
        {"href": "/a"}, {"href": "https://other.org/"},
        {"href": "javascript:alert(1)"}, {"href": "/a#fragment"},
        {"href": "/?token=123"},
    ]
    assert in_scope_links("https://example.org/", links, "https://example.org/") == [
        "https://example.org/a"
    ]
