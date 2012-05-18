import zlib
import re

from django.conf import settings

from versions.compare import version_re

pattern_plus = re.compile(r'((\d+)\+)')


def floor_version(s):
    result = s
    if result:
        s = s.replace('.x', '.0').replace('.*', '.0').replace('*', '.0')
        match = re.match(version_re, s)
        if match:
            major, minor = match.groups()[:2]
            major, minor = int(major), int(minor or 0)
            result = '%s.%s' % (major, minor)
    return result


def convert_version(version_string):
    """
    This will enumerate a version so that it can be used for comparisons and
    indexing.
    """

    # Replace .x or .* with .99 since these are equivalent.
    version_string = version_string.replace('.x', '.99')
    version_string = version_string.replace('.*', '.99')
    # Replace any leftover * with .99 (e.g., 4.0* => 4.0.99).
    version_string = version_string.replace('*', '.99')

    # Replace \d+\+ with $1++pre0 (e.g. 2.1+ => 2.2pre0).

    match = re.search(pattern_plus, version_string)

    if match:
        (old, ver) = match.groups()
        replacement = "%dpre0" % (int(ver) + 1)
        version_string = version_string.replace(old, replacement)

    # Now we break up a version into components.
    #
    # e.g. 3.7.2.1b3pre3
    # we break into:
    # major => 3
    # minor1 => 7
    # minor2 => 2
    # minor3 => 1
    # alpha => b => 1
    # alpha_n => 3
    # pre => 0
    # pre_n => 3
    #
    # Alpha is 0,1,2 based on whether a version is alpha, beta or a release.
    # Pre is 0 or 1.  0 indicates that this is a pre-release.
    #
    # The numbers are chosen based on sorting rules, not for any deep meaning.

    match = re.match(version_re, version_string)

    if match:
        (major, minor1, minor2, minor3, alpha, alpha_n, pre,
            pre_n) = match.groups()

        # normalize data
        major  = int(major)
        minor1 = int(minor1 or 0)
        minor2 = int(minor2 or 0)
        minor3 = int(minor3 or 0)

        if alpha == 'a':
            alpha = 0
        elif alpha == 'b':
            alpha = 1
        else:
            alpha = 2

        if alpha_n:
            alpha_n = int(alpha_n)
        else:
            alpha_n = 0

        if pre == 'pre':
            pre = 0
        else:
            pre = 1

        if pre_n:
            pre_n = int(pre_n)
        else:
            pre_n = 0

        # We recombine everything into a single large integer.
        int_str = ("%02d%02d%02d%02d%d%02d%d%02d"
            % (major, minor1, minor2, minor3, alpha, alpha_n, pre, pre_n))

        return int(int_str)


crc32 = lambda x: zlib.crc32(x) & 0xffffffff
