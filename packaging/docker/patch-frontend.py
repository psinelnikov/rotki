#!/usr/bin/env python3
"""Patch the compiled frontend JS to remove premium feature restrictions.

Works across different build hashes by using structural regex patterns
and dynamically discovering minified variable names.
"""
import glob
import re
import sys


def patch_file(path: str) -> bool:
    """Patch a single use-feature-access JS file. Returns True if changed."""
    with open(path) as f:
        content = f.read()
    original = content

    # 1. Remove the premium-status guard at the start of the allowed computed:
    #    if(!VAR(VAR))return!1;
    content = re.sub(r'if\(!\w+\(\w+\)\)return!1;', '', content)

    # 2. Replace the capability enabled-check false-fallback with always-true:
    #    VAR?.[VAR]?.enabled??!1  ->  !0
    content = re.sub(r'\w+\?\.\[\w+\]\?\.enabled\?\?!1', '!0', content)

    # 3. Change default tier label from "Free" to "SelfHosted"
    content = content.replace('??"Free"', '??"SelfHosted"')

    # 4. Make the premium return value always true.
    #    Discover the shallowRef (s) and computed (a) aliases from the file
    #    by looking at how other return values are wrapped:
    #      allowed:s(...)  ->  s = shallowRef
    #      =a(()=>{        ->  a = computed
    s_match = re.search(r'allowed:(\w+)\(', content)
    a_match = re.search(r'=(\w+)\(\(\)=>', content)

    if s_match and a_match:
        s_var, a_var = s_match.group(1), a_match.group(1)
        # Only replace premium in the return statement (followed by }export),
        # not in the destructuring assignment
        content = re.sub(
            r'premium:(\w+)(\}\}export)',
            lambda m: f'premium:{s_var}({a_var}(()=>!0)){m.group(2)}',
            content,
        )
    else:
        # Fallback: set premium to plain true
        content = re.sub(r'premium:\w+\}', 'premium:!0}', content)

    if content != original:
        with open(path, 'w') as f:
            f.write(content)
        return True
    return False


def main() -> None:
    files = glob.glob('/opt/rotki/frontend/use-feature-access-*.js')
    if not files:
        print('ERROR: use-feature-access-*.js not found', file=sys.stderr)
        sys.exit(1)

    patched = False
    for path in files:
        if patch_file(path):
            print(f'Patched {path}')
            patched = True
        else:
            print(f'WARNING: no changes in {path}', file=sys.stderr)

    if not patched:
        print('ERROR: no files were patched', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
