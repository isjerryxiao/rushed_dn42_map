import bz2
import json

def decode(entry: dict) -> None:
    if entry["type"] == "metadata":
        print(json.dumps(entry, indent=2))
    elif entry["type"] in {"ipv4", "ipv6"}:
        for rib in entry["rib"]:
            print("%s_prefix:" % entry["type"], entry["prefix"])
            path_attrs = ('as_set', 'as_sequence', 'as_confed_sequence', 'as_confed_set')
            attrs = (*path_attrs, "community", "extended_community", "large_community")
            for attr in attrs:
                attr_val = rib.get(attr)
                if attr_val:
                    print(attr, ":", attr_val)
            assert not any(filter(lambda x: x not in attrs, rib))
    else:
        assert False

with bz2.BZ2File("parsed.jsonl.bz2", 'r') as f:
    while line := f.readline():
        entry = json.loads(line)
        decode(entry)
        input("continue?")
