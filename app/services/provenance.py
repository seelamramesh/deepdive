"""Conservative material grouping; distinct groups do not prove independence."""
import re
from urllib.parse import urlparse


def repository_title(source):
    host = urlparse(source.url).hostname
    if host == "arxiv.org":
        title = re.sub(r"^\[\d{4}\.\d{4,5}(?:v\d+)?\]\s*", "", source.title)
    elif host == "iopscience.iop.org":
        title = re.sub(r"\s*-\s*IOPscience$", "", source.title, flags=re.I)
    else:
        return None
    title = " ".join(title.casefold().split())
    return title if len(title) >= 60 else None


def material_groups(sources):
    parents = {s.id:s.id for s in sources}
    def root(key):
        while parents[key] != key:
            key = parents[key]
        return key
    seen = {}
    title_hosts = {}
    for source in sources:
        title = repository_title(source)
        if title:
            title_hosts.setdefault(title,set()).add(urlparse(source.url).hostname)
    for source in sources:
        keys = list(source.work_identifiers)
        title = repository_title(source)
        if title and title_hosts[title] == {"arxiv.org", "iopscience.iop.org"}:
            keys.append("probable_journal_preprint_title:" + title)
        if source.content_hash:
            keys.append("snapshot:" + source.content_hash)
        for key in keys:
            if key in seen:
                parents[root(source.id)] = root(seen[key])
            else:
                seen[key] = source.id
    return {s.id:root(s.id) for s in sources}
