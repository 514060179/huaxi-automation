from integration_harness.video import choose_m3u8_url, parse_m3u8


def test_parse_m3u8_builds_absolute_segment_urls():
    content = """#EXTM3U
#EXTINF:10.0,
segment-00001.ts
#EXTINF:9.5,
segment-00002.ts
"""
    segments = parse_m3u8(content, "https://v1.hxacc.com/path/playlist.m3u8")
    assert len(segments) == 2
    assert segments[0].url == "https://v1.hxacc.com/path/segment-00001.ts"
    assert segments[1].duration == 9.5


def test_choose_m3u8_url_defaults_to_fd():
    doc_info = {
        "source": {
            "FD": "https://v1.hxacc.com/example-fd.m3u8",
            "LD": "https://v1.hxacc.com/example-ld.m3u8",
        }
    }

    assert choose_m3u8_url(doc_info) == "https://v1.hxacc.com/example-fd.m3u8"
